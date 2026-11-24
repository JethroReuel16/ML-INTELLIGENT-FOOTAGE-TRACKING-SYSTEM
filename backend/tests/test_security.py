"""Security and reliability hardening (backend review)."""

import os
import subprocess
import sys

import pytest
from fastapi import HTTPException

from app.config import settings
from tests.conftest import PASSWORD, VIDEO_BYTES, register_and_login, upload_search


@pytest.fixture
def configure():
    """Temporarily override frozen settings fields; restored afterwards."""
    original = {}

    def apply(**values):
        for key, value in values.items():
            original.setdefault(key, getattr(settings, key))
            object.__setattr__(settings, key, value)

    yield apply

    for key, value in original.items():
        object.__setattr__(settings, key, value)


# ---------------------------------------------------------------- registration


def test_registration_is_closed_in_production(client, configure):
    configure(environment="production", registration_enabled=None, cookie_secure=False)
    assert client.get("/api/auth/config").json() == {"registration_enabled": False}
    r = client.post("/api/auth/register", json={"full_name": "Eve", "email": "eve@example.org", "password": PASSWORD})
    assert r.status_code == 403


def test_registration_can_be_enabled_explicitly(client, configure):
    configure(environment="production", registration_enabled=True, cookie_secure=False)
    assert client.get("/api/auth/config").json()["registration_enabled"] is True
    register_and_login(client)


# ---------------------------------------------------------------- file sources


def test_production_blocks_file_sources_without_allow_list(client, configure, tmp_path):
    secret = tmp_path / "private.mp4"
    secret.write_bytes(b"PRIVATE" + VIDEO_BYTES)
    register_and_login(client, "stranger@example.org", "Stranger")

    configure(environment="production", allowed_source_roots=[], cookie_secure=False)
    r = client.post("/api/sources", json={"name": "x", "source_type": "local", "url": str(secret)})
    assert r.status_code == 403
    assert "ALLOWED_SOURCE_ROOTS" in r.json()["detail"]


def test_previously_registered_file_source_cannot_be_used_or_tested(client, configure, tmp_path):
    secret = tmp_path / "private.mp4"
    secret.write_bytes(b"PRIVATE" + VIDEO_BYTES)
    register_and_login(client)
    sid = client.post("/api/sources", json={"name": "x", "source_type": "local", "url": str(secret)}).json()["id"]

    # Policy tightened after registration: every use is re-checked.
    configure(environment="production", allowed_source_roots=[], cookie_secure=False)
    assert client.post(f"/api/sources/{sid}/test").status_code == 403
    r = client.post("/api/search/source", data={"source_id": sid, "text_prompt": "bag"})
    assert r.status_code == 403
    assert client.get("/api/search").json() == []  # nothing was searched or leaked


def test_allow_list_permits_inside_and_blocks_outside(client, configure, tmp_path):
    allowed = tmp_path / "footage"
    allowed.mkdir()
    inside = allowed / "cam.mp4"
    inside.write_bytes(VIDEO_BYTES)
    outside = tmp_path / "elsewhere.mp4"
    outside.write_bytes(VIDEO_BYTES)
    sneaky = allowed / ".." / "elsewhere.mp4"  # traversal back out

    configure(allowed_source_roots=[str(allowed)])
    register_and_login(client)
    ok = client.post("/api/sources", json={"name": "in", "source_type": "local", "url": str(inside)})
    assert ok.status_code == 201
    for path in (outside, sneaky):
        r = client.post("/api/sources", json={"name": "out", "source_type": "local", "url": str(path)})
        assert r.status_code == 403, path


# ---------------------------------------------------------------- SSRF


@pytest.mark.parametrize("url", [
    "http://169.254.169.254/latest/meta-data/x.mp4",
    "https://[fe80::1]/x.mp4",
    "rtsp://169.254.10.10/stream",
    "http://0.0.0.0/x.mp4",
])
def test_metadata_and_link_local_targets_are_refused(client, url):
    register_and_login(client)
    kind = "rtsp" if url.startswith("rtsp") else "http"
    r = client.post("/api/sources", json={"name": "x", "source_type": kind, "url": url})
    assert r.status_code == 403, r.text


def test_loopback_refused_in_production_allowed_in_development(client, configure):
    register_and_login(client)
    body = {"name": "x", "source_type": "http", "url": "http://127.0.0.1:9/x.mp4"}
    assert client.post("/api/sources", json=body).status_code == 201

    configure(environment="production", loopback_sources=None, cookie_secure=False)
    assert client.post("/api/sources", json=body).status_code == 403


def test_private_lan_camera_registration(client):
    register_and_login(client)
    r = client.post("/api/sources", json={"name": "NVR", "source_type": "rtsp", "url": "rtsp://user:pw@192.168.1.64:554/s1"})
    assert r.status_code == 201


def test_http_redirects_to_metadata_are_blocked():
    from urllib.request import Request

    from app.api.routes.search import _CheckedRedirectHandler

    handler = _CheckedRedirectHandler()
    req = Request("http://example.org/video.mp4")
    with pytest.raises(HTTPException) as caught:
        handler.redirect_request(req, None, 302, "Found", {}, "http://169.254.169.254/latest/x")
    assert caught.value.status_code == 403
    with pytest.raises(HTTPException):
        handler.redirect_request(req, None, 302, "Found", {}, "file:///etc/passwd")


# ---------------------------------------------------------------- request guards


def test_cross_site_state_changes_are_refused(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "a@example.org", "password": "x"},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403

    allowed = client.post(
        "/api/auth/login",
        json={"email": "a@example.org", "password": "x"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert allowed.status_code == 401  # reaches the endpoint
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_oversized_upload_rejected_before_reading(client, monkeypatch):
    import main

    register_and_login(client)
    monkeypatch.setattr(main, "MAX_REQUEST_BYTES", 100)
    r = upload_search(client)
    assert r.status_code == 413


# ---------------------------------------------------------------- login timing


def test_unknown_email_still_runs_password_hashing(client, monkeypatch):
    from app.api.routes import auth

    calls = []
    real = auth.verify_password
    monkeypatch.setattr(auth, "verify_password", lambda p, h: calls.append(h) or real(p, h))

    r = client.post("/api/auth/login", json={"email": "nobody@example.org", "password": "whatever"})
    assert r.status_code == 401
    assert calls, "verify_password must run even when the account does not exist"


# ---------------------------------------------------------------- DB connections


def test_no_transaction_is_held_while_the_pipeline_runs(client, monkeypatch):
    import main
    from app.database import get_db
    from app.services import search_service as module
    from tests.conftest import fake_run_search

    sessions = []
    override = main.app.dependency_overrides[get_db]

    def tracking_override():
        for db in override():
            sessions.append(db)
            yield db

    main.app.dependency_overrides[get_db] = tracking_override
    states = []

    def spy(*args, **kwargs):
        states.append([db.in_transaction() for db in sessions])
        return fake_run_search(*args, **kwargs)

    monkeypatch.setattr(module.search_service, "run_search", spy)
    register_and_login(client)
    assert upload_search(client).status_code == 200
    assert states and not any(states[-1]), states


# ---------------------------------------------------------------- admin CLI


def test_manage_create_list_and_deactivate(client, engine, monkeypatch, capsys):
    from sqlalchemy.orm import sessionmaker

    import app.database
    import manage

    monkeypatch.setattr(app.database, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setenv("MLFT_NEW_PASSWORD", PASSWORD)

    assert manage.main(["create-user", "--email", "Admin@Example.org", "--name", "Ada Admin"]) == 0
    with pytest.raises(SystemExit):
        manage.main(["create-user", "--email", "admin@example.org", "--name", "Dup"])

    r = client.post("/api/auth/login", json={"email": "admin@example.org", "password": PASSWORD})
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    manage.main(["list-users"])
    assert "admin@example.org" in capsys.readouterr().out

    manage.main(["set-active", "--email", "admin@example.org", "--inactive"])
    assert client.get("/api/auth/me").status_code == 401  # signed out everywhere


# ---------------------------------------------------------------- config


def test_relative_storage_dir_is_anchored_to_backend(monkeypatch):
    from app import config

    monkeypatch.setenv("STORAGE_DIR", "./data-store")
    assert config._storage_dir() == os.path.join(config.BACKEND_DIR, "data-store")


def test_wildcard_cors_is_rejected_at_startup():
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-c", "import app.config"],
        cwd=backend,
        env={**os.environ, "CORS_ORIGINS": "*"},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "CORS_ORIGINS cannot be '*'" in result.stderr
