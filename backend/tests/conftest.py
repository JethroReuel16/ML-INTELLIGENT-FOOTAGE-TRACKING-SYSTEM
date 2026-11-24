"""
Test fixtures.

The suite runs the real FastAPI app against PostgreSQL, but every table is
created in the session-private ``pg_temp`` schema of a single connection, so
nothing touches existing data and everything disappears when the connection
closes. The ML pipeline is replaced by a fast fake.
"""

import os
import shutil
import tempfile
import uuid

import pytest

# Isolated storage for uploads/results, configured before the app is imported.
_STORAGE = tempfile.mkdtemp(prefix="mlft-test-")
os.environ["STORAGE_DIR"] = _STORAGE
os.environ["LOGIN_MAX_ATTEMPTS"] = "3"
os.environ.setdefault("APP_ENV", "development")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
import app.models  # noqa: E402,F401
from app.services import search_service as search_service_module  # noqa: E402
from app.storage import RESULTS_DIR  # noqa: E402
import main  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={"options": "-c search_path=pg_temp"},
    )
    with eng.begin() as conn:
        Base.metadata.create_all(conn)
        # Safety: refuse to run unless the tables really are temporary.
        schema = conn.execute(text("select current_schema()")).scalar()
        assert schema.startswith("pg_temp"), f"tests must use temp tables, got {schema}"
    yield eng
    eng.dispose()
    shutil.rmtree(_STORAGE, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables(engine):
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    from app.api.routes import auth

    auth._attempts.clear()


@pytest.fixture
def client(engine, monkeypatch):
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(search_service_module.search_service, "run_search", fake_run_search)

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()


def fake_run_search(video_path, reference_image=None, **kwargs):
    """Stand-in for the ML pipeline: two matches with real evidence files."""
    search_id = f"search_test_{uuid.uuid4().hex[:10]}"
    evidence_dir = os.path.join(RESULTS_DIR, search_id, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    matches = []
    for rank, track in ((1, 7), (2, 3)):
        path = os.path.join(evidence_dir, f"rank_{rank:02d}_track_{track}.jpg")
        with open(path, "wb") as fh:
            fh.write(b"\xff\xd8\xff\xe0fake-jpeg")
        matches.append({
            "rank": rank,
            "track_id": track,
            "class_id": 24,
            "class_name": "backpack",
            "match_status": "TOP CANDIDATE" if rank == 1 else "CANDIDATE",
            "similarity_score": 0.9 - rank / 10,
            "ranking_score": 0.9 - rank / 10,
            "top3_average": 0.8,
            "average_similarity": 0.7,
            "timestamp": 1.5 * rank,
            "frame_number": 30 * rank,
            "bbox": [1, 2, 3, 4],
            "detection_confidence": 0.88,
            "frames_observed": 4,
            "evidence_image": path,
        })

    return {
        "status": "completed",
        "search_id": search_id,
        "created_at": "2026-11-23T10:00:00",
        "reference": {"image": reference_image, "text_prompt": kwargs.get("text_prompt")},
        "video": {"path": video_path, "duration": 10.0, "fps": 25.0, "frame_count": 250, "width": 640, "height": 360},
        "search": {
            "search_mode": kwargs.get("search_mode") or "image",
            "text_prompt": kwargs.get("text_prompt"),
            "frame_interval": kwargs.get("frame_interval"),
            "minimum_detection_confidence": kwargs.get("min_detection_confidence"),
            "frames_analyzed": 50,
            "candidate_observations": 9,
            "unique_tracks": 2,
            "candidates": 2,
        },
        "matches": matches,
    }


# ---------------------------------------------------------------- helpers

PASSWORD = "correct-horse-1"


def register_and_login(client, email="ana@example.org", name="Ana Phiri"):
    r = client.post("/api/auth/register", json={"full_name": name, "email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["user"]


VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"0123456789" * 100


def upload_search(client, text_prompt=None, image=True):
    files = {"video": ("clip.mp4", VIDEO_BYTES, "video/mp4")}
    if image:
        files["reference_image"] = ("ref.jpg", b"\xff\xd8\xff\xe0img", "image/jpeg")
    data = {"frame_interval": "5", "min_detection_confidence": "0.25", "max_results": "20"}
    if text_prompt:
        data["text_prompt"] = text_prompt
    return client.post("/api/search", files=files, data=data)
