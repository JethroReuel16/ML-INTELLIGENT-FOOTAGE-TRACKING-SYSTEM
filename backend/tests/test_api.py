import pytest
import os
import threading
import time

from tests.conftest import (
    PASSWORD,
    VIDEO_BYTES,
    register_and_login,
    upload_search,
)


# ---------------------------------------------------------------- health


def test_health_and_readiness(client):
    assert client.get("/health").json()["status"] == "healthy"
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["database"] == "ok"


# ---------------------------------------------------------------- auth


def test_protected_routes_require_session(client):
    for path in ("/api/auth/me", "/api/search", "/api/sources", "/api/search/x/video"):
        assert client.get(path).status_code == 401, path


def test_register_login_me_logout(client):
    user = register_and_login(client)
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == user["email"]

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_registration_rejected(client):
    register_and_login(client)
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Ana Again", "email": "ANA@example.org", "password": PASSWORD},
    )
    assert r.status_code == 409


def test_login_is_throttled_after_repeated_failures(client):
    register_and_login(client)
    client.post("/api/auth/logout")
    for _ in range(3):
        assert client.post("/api/auth/login", json={"email": "ana@example.org", "password": "wrong"}).status_code == 401
    blocked = client.post("/api/auth/login", json={"email": "ana@example.org", "password": PASSWORD})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_session_cookie_flags(client):
    client.post("/api/auth/register", json={"full_name": "Ana", "email": "c@example.org", "password": PASSWORD})
    r = client.post("/api/auth/login", json={"email": "c@example.org", "password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


# ---------------------------------------------------------------- sources


def test_source_crud_uses_patch_and_masks_credentials(client):
    register_and_login(client)
    created = client.post(
        "/api/sources",
        json={"name": "Gate", "source_type": "rtsp", "url": "rtsp://admin:secret@10.0.0.5:554/s1"},
    )
    assert created.status_code == 201, created.text
    source = created.json()
    assert source["has_credentials"] is True
    assert "secret" not in source["display_url"]

    # The frontend sends PATCH (it used to send an unsupported PUT).
    patched = client.patch(f"/api/sources/{source['id']}", json={"name": "Main gate", "location": "North"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Main gate"
    assert client.put(f"/api/sources/{source['id']}", json={}).status_code == 405

    assert client.delete(f"/api/sources/{source['id']}").status_code == 200
    assert client.get("/api/sources").json() == []


def test_file_source_must_point_at_a_video(client):
    register_and_login(client)
    r = client.post("/api/sources", json={"name": "Folder", "source_type": "local", "url": os.path.abspath(os.sep)})
    assert r.status_code == 400
    assert "video file" in r.json()["detail"]


def test_sources_are_isolated_between_users(client):
    register_and_login(client, "a@example.org")
    sid = client.post(
        "/api/sources", json={"name": "Cam", "source_type": "http", "url": "https://example.org/a.mp4"}
    ).json()["id"]
    client.post("/api/auth/logout")

    register_and_login(client, "b@example.org", "Bo")
    assert client.get("/api/sources").json() == []
    assert client.patch(f"/api/sources/{sid}", json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/sources/{sid}").status_code == 404


# ---------------------------------------------------------------- search + results


def test_upload_search_result_evidence_and_video(client):
    register_and_login(client)
    r = upload_search(client)
    assert r.status_code == 200, r.text
    search_id = r.json()["result"]["search_id"]

    history = client.get("/api/search").json()
    assert [h["search_id"] for h in history] == [search_id]
    assert history[0]["top_match"]["rank"] == 1

    result = client.get(f"/api/search/{search_id}").json()
    assert len(result["matches"]) == 2

    evidence_name = os.path.basename(result["matches"][0]["evidence_image"])
    ev = client.get(f"/api/search/{search_id}/evidence/{evidence_name}")
    assert ev.status_code == 200 and ev.headers["content-type"] == "image/jpeg"

    # New: original footage streaming with HTTP Range support.
    full = client.get(f"/api/search/{search_id}/video")
    assert full.status_code == 200
    assert full.content == VIDEO_BYTES
    assert full.headers["content-disposition"].startswith("inline")

    part = client.get(f"/api/search/{search_id}/video", headers={"Range": "bytes=0-9"})
    assert part.status_code == 206
    assert part.content == VIDEO_BYTES[:10]


def test_text_only_search(client):
    register_and_login(client)
    r = upload_search(client, text_prompt="red backpack", image=False)
    assert r.status_code == 200, r.text
    assert r.json()["result"]["search"]["search_mode"] == "text"


def test_results_are_isolated_between_users(client):
    register_and_login(client, "a@example.org")
    search_id = upload_search(client).json()["result"]["search_id"]
    client.post("/api/auth/logout")

    register_and_login(client, "b@example.org", "Bo")
    assert client.get("/api/search").json() == []
    assert client.get(f"/api/search/{search_id}").status_code == 404
    assert client.get(f"/api/search/{search_id}/video").status_code == 404


def test_upload_validation(client):
    register_and_login(client)

    not_video = client.post(
        "/api/search",
        files={
            "video": ("notes.txt", b"hello", "text/plain"),
            "reference_image": ("ref.jpg", b"img", "image/jpeg"),
        },
    )
    assert not_video.status_code == 400

    too_many = client.post(
        "/api/search",
        files={"video": ("clip.mp4", VIDEO_BYTES, "video/mp4"), "reference_image": ("r.jpg", b"i", "image/jpeg")},
        data={"max_results": "1000"},
    )
    assert too_many.status_code == 400

    no_input = client.post("/api/search", files={"video": ("clip.mp4", VIDEO_BYTES, "video/mp4")})
    assert no_input.status_code == 400


def test_octet_stream_video_with_known_extension_is_accepted(client):
    register_and_login(client)
    r = client.post(
        "/api/search",
        files={
            "video": ("clip.mkv", VIDEO_BYTES, "application/octet-stream"),
            "reference_image": ("ref.png", b"\x89PNG", "image/png"),
        },
    )
    assert r.status_code == 200, r.text


def test_multi_source_keeps_per_source_rank_and_settings(client, tmp_path):
    register_and_login(client)
    ids = []
    for name in ("Cam A", "Cam B"):
        video = tmp_path / f"{name.replace(' ', '_')}.mp4"
        video.write_bytes(VIDEO_BYTES)
        ids.append(
            client.post("/api/sources", json={"name": name, "source_type": "local", "url": str(video)}).json()["id"]
        )

    r = client.post(
        "/api/search/multi-source",
        data={"source_ids": f'["{ids[0]}", "{ids[1]}"]', "text_prompt": "backpack"},
        files={"reference_image": ("ref.jpg", b"\xff\xd8img", "image/jpeg")},
    )
    assert r.status_code == 200, r.text
    multi_id = r.json()["multi_search_id"]

    data = client.get(f"/api/search/multi/{multi_id}").json()
    assert data["status"] == "completed"
    assert data["settings"]["search_mode"] == "image_text"
    assert data["settings"]["text_prompt"] == "backpack"
    assert len(data["matches"]) == 4
    # Global ranking is 1..4, but each match still knows its rank inside
    # its own source search (used by the evidence viewer).
    assert sorted(m["rank"] for m in data["matches"]) == [1, 2, 3, 4]
    assert sorted(m["source_rank"] for m in data["matches"]) == [1, 1, 2, 2]


def test_failed_search_cleans_up_uploads(client, monkeypatch):
    from app.services import search_service as module
    from app.storage import UPLOADS_DIR

    register_and_login(client)
    before = set(os.listdir(UPLOADS_DIR))

    def boom(*args, **kwargs):
        raise RuntimeError("model crashed")

    monkeypatch.setattr(module.search_service, "run_search", boom)
    r = upload_search(client)
    assert r.status_code == 500
    assert "model crashed" not in r.text  # internals are not leaked
    assert set(os.listdir(UPLOADS_DIR)) == before


def test_search_does_not_block_other_requests(client, monkeypatch):
    """A long-running search must not freeze the server (it used to)."""
    from app.services import search_service as module
    from tests.conftest import fake_run_search

    def slow_search(*args, **kwargs):
        time.sleep(2)
        return fake_run_search(*args, **kwargs)

    monkeypatch.setattr(module.search_service, "run_search", slow_search)
    register_and_login(client)

    done = {}
    worker = threading.Thread(target=lambda: done.setdefault("r", upload_search(client)))
    worker.start()
    time.sleep(0.5)

    started = time.monotonic()
    assert client.get("/health").status_code == 200
    elapsed = time.monotonic() - started
    worker.join()

    assert done["r"].status_code == 200
    assert elapsed < 1.0, f"health check waited {elapsed:.1f}s behind the search"


# ---------------------------------------------------------------- system review additions


def _make_local_source(client, tmp_path, name):
    video = tmp_path / f"{name.replace(' ', '_')}.mp4"
    video.write_bytes(VIDEO_BYTES)
    return client.post("/api/sources", json={"name": name, "source_type": "local", "url": str(video)}).json()


def test_result_and_history_report_their_source(client, tmp_path):
    register_and_login(client)
    source = _make_local_source(client, tmp_path, "Gate cam")

    r = client.post(
        "/api/search/source",
        data={"source_id": source["id"], "text_prompt": "backpack"},
    )
    assert r.status_code == 200, r.text
    search_id = r.json()["result"]["search_id"]

    result = client.get(f"/api/search/{search_id}").json()
    assert result["source"]["name"] == "Gate cam"
    assert "files" not in result  # no server paths leaked

    history = client.get("/api/search").json()
    assert history[0]["source"]["name"] == "Gate cam"


def test_multi_source_searches_can_be_listed_later(client, tmp_path):
    register_and_login(client)
    ids = [_make_local_source(client, tmp_path, n)["id"] for n in ("A", "B")]
    multi_id = client.post(
        "/api/search/multi-source",
        data={"source_ids": f'["{ids[0]}", "{ids[1]}"]', "text_prompt": "bag"},
    ).json()["multi_search_id"]

    listed = client.get("/api/search/multi").json()
    assert [m["multi_search_id"] for m in listed] == [multi_id]
    assert listed[0]["match_count"] == 4
    assert sorted(listed[0]["source_names"]) == ["A", "B"]
    assert listed[0]["text_prompt"] == "bag"


def test_delete_search_removes_rows_and_files(client):
    from app.storage import RESULTS_DIR, UPLOADS_DIR

    register_and_login(client)
    search_id = upload_search(client).json()["result"]["search_id"]
    result_dir = os.path.join(RESULTS_DIR, search_id)
    upload_dir = os.path.dirname(
        client.get(f"/api/search/{search_id}").json()["video"]["path"]
    )
    assert os.path.isdir(result_dir) and os.path.isdir(upload_dir)

    assert client.delete(f"/api/search/{search_id}").status_code == 200
    assert client.get(f"/api/search/{search_id}").status_code == 404
    assert client.get("/api/search").json() == []
    assert not os.path.exists(result_dir)
    assert not os.path.exists(upload_dir)
    # The storage roots themselves are never removed.
    assert os.path.isdir(RESULTS_DIR) and os.path.isdir(UPLOADS_DIR)


def test_users_cannot_delete_each_others_searches(client):
    register_and_login(client, "a@example.org")
    search_id = upload_search(client).json()["result"]["search_id"]
    client.post("/api/auth/logout")

    register_and_login(client, "b@example.org", "Bo")
    assert client.delete(f"/api/search/{search_id}").status_code == 404
    client.post("/api/auth/logout")

    client.post("/api/auth/login", json={"email": "a@example.org", "password": PASSWORD})
    assert client.get(f"/api/search/{search_id}").status_code == 200


def test_multi_result_hides_matches_of_deleted_searches(client, tmp_path):
    register_and_login(client)
    ids = [_make_local_source(client, tmp_path, n)["id"] for n in ("A", "B")]
    multi = client.post(
        "/api/search/multi-source",
        data={"source_ids": f'["{ids[0]}", "{ids[1]}"]', "text_prompt": "bag"},
    ).json()["result"]

    first_search = multi["sources"][0]["search_id"]
    client.delete(f"/api/search/{first_search}")

    data = client.get(f"/api/search/multi/{multi['multi_search_id']}").json()
    assert len(data["matches"]) == 2
    assert all(m["search_id"] != first_search for m in data["matches"])


def test_high_detail_flag_reaches_the_pipeline(client, monkeypatch):
    from app.services import search_service as module
    from tests.conftest import fake_run_search

    seen = {}

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return fake_run_search(*args, **kwargs)

    monkeypatch.setattr(module.search_service, "run_search", spy)
    register_and_login(client)
    r = client.post(
        "/api/search",
        files={"video": ("clip.mp4", VIDEO_BYTES, "video/mp4")},
        data={"text_prompt": "shoe", "high_detail": "true"},
    )
    assert r.status_code == 200, r.text
    assert seen["high_detail"] is True


# ---------------------------------------------------------------- ML engine integration


def test_unreadable_video_gives_a_clear_400(client, monkeypatch):
    from app.services import search_service as module
    from video.processor import VideoReadError

    def broken(*args, **kwargs):
        raise VideoReadError("The video could not be opened. It may be corrupt, incomplete or in an unsupported format.")

    monkeypatch.setattr(module.search_service, "run_search", broken)
    register_and_login(client)
    r = upload_search(client)
    assert r.status_code == 400
    assert "could not be opened" in r.json()["detail"]


def test_models_load_once_under_concurrent_first_searches(monkeypatch):
    import threading
    import time

    from app.services import search_service as module

    built = []

    class SlowPipeline:
        def __init__(self, **kwargs):
            time.sleep(0.3)
            built.append(1)
            self.detector_status = {"active": "yoloe", "device": "cpu", "fallback": False}

    monkeypatch.setattr(module, "VisionTracePipeline", SlowPipeline)
    service = module.SearchService()
    assert service.status() == {"state": "not_loaded"}

    threads = [threading.Thread(target=service._get_pipeline) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(built) == 1
    assert service.status() == {"state": "ready", "detector": "yoloe", "device": "cpu", "fallback": False}


def test_model_load_failure_is_reported_and_retried(monkeypatch):
    from app.services import search_service as module

    attempts = []

    class Broken:
        def __init__(self, **kwargs):
            attempts.append(1)
            raise RuntimeError("weights missing")

    monkeypatch.setattr(module, "VisionTracePipeline", Broken)
    service = module.SearchService()
    for _ in range(2):
        with pytest.raises(RuntimeError):
            service._get_pipeline()
    assert len(attempts) == 2  # not cached as a permanent failure
    assert service.status()["state"] == "error"
    assert "weights missing" in service.status()["error"]


def test_readiness_reports_ml_state(client):
    body = client.get("/health/ready").json()
    assert body["status"] == "ready"
    assert "state" in body["ml"]
