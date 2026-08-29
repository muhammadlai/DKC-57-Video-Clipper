"""
test_api.py — REST API endpoints (TestClient, pipeline mocked).
"""

import asyncio
import io
import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    import api

    with TestClient(api.app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["app"] == "AITZAZ AI"
    assert isinstance(data["ffmpeg"], bool)


def test_stats_initial(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    for key in ("videos", "shorts", "processing", "failed"):
        assert key in r.json()


def test_create_project_invalid_url(client):
    r = client.post("/api/projects", json={"youtube_url": "https://example.com/v"})
    assert r.status_code == 400


def test_create_project_valid(client, monkeypatch):
    import api

    calls = []
    monkeypatch.setattr(
        api, "_run_pipeline",
        lambda project_id: calls.append(project_id) or None,
    )
    r = client.post(
        "/api/projects",
        json={
            "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
            "settings": {
                "num_clips": 3,
                "min_duration": 20,
                "max_duration": 60,
                "captions": "classic_white",
                "face_tracking": False,
                "ai_detection": False,
                "watermark": {"enabled": True, "position": "top_left", "opacity": 0.4},
            },
        },
    )
    assert r.status_code == 201, r.text
    pid = r.json()["project_id"]
    assert pid in calls  # pipeline was scheduled

    got = client.get(f"/api/projects/{pid}")
    assert got.status_code == 200
    body = got.json()
    assert body["status"] == "pending"
    assert body["config"]["num_clips"] == 3
    assert body["config"]["face_tracking"] is False
    assert body["config"]["watermark"]["position"] == "top_left"
    client.delete(f"/api/projects/{pid}")


def test_upload_local_video(client, monkeypatch):
    import api

    monkeypatch.setattr(
        api, "_run_pipeline",
        lambda project_id: None,
    )
    content = b"fake-mp4-bytes" * 100
    r = client.post(
        "/api/projects/upload",
        files={"file": ("My Podcast.mp4", io.BytesIO(content), "video/mp4")},
        data={"settings_json": json.dumps({"num_clips": 2})},
    )
    assert r.status_code == 201, r.text
    pid = r.json()["project_id"]

    got = client.get(f"/api/projects/{pid}")
    assert got.status_code == 200
    body = got.json()
    assert body["source_type"] == "upload"
    assert body["title"] == "My Podcast"
    assert body["config"]["num_clips"] == 2
    assert body["source_file"]
    assert os.path.isfile(body["source_file"])
    assert os.path.getsize(body["source_file"]) == len(content)

    # cleanup
    client.delete(f"/api/projects/{pid}")


def test_upload_rejects_bad_extension(client):
    r = client.post(
        "/api/projects/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    assert r.status_code == 400


def test_bulk_create(client, monkeypatch):
    import api

    created = []
    monkeypatch.setattr(
        api, "_run_pipeline",
        lambda project_id: created.append(project_id) or None,
    )
    r = client.post(
        "/api/projects/bulk",
        json={
            "youtube_urls": [
                "https://youtu.be/aaa",
                "https://youtu.be/bbb",
                "not-a-url",
            ],
            "settings": {"num_clips": 1},
        },
    )
    assert r.status_code == 201, r.text
    projects = r.json()["projects"]
    assert len(projects) == 2  # invalid URL skipped
    assert len(created) == 2

    for p in projects:
        client.delete(f"/api/projects/{p['project_id']}")


def test_retry_and_cancel_flow(client, monkeypatch):
    import api
    import database

    # create a project via the API
    r = client.post("/api/projects", json={"youtube_url": "https://youtu.be/retry-test"})
    assert r.status_code == 201
    pid = r.json()["project_id"]
    pid = r.json()["project_id"]

    # mark done, then retry
    import threading
    loop = asyncio.new_event_loop()
    loop.run_until_complete(database.update_project_status(pid, "done"))
    loop.close()

    monkeypatch.setattr(api, "_run_pipeline", lambda project_id: None)
    r = client.post(f"/api/projects/{pid}/retry")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "retrying"

    # retry while already running -> 409
    loop = asyncio.new_event_loop()
    loop.run_until_complete(database.update_project_status(pid, "processing"))
    loop.close()
    r = client.post(f"/api/projects/{pid}/retry")
    assert r.status_code == 409

    # cancel while running -> ok
    r = client.post(f"/api/projects/{pid}/cancel")
    assert r.status_code == 200, r.text
    assert api._cancel_events[pid].is_set()

    # cancel a non-running project -> 409
    loop = asyncio.new_event_loop()
    loop.run_until_complete(database.update_project_status(pid, "done"))
    loop.close()
    r = client.post(f"/api/projects/{pid}/cancel")
    assert r.status_code == 409

    client.delete(f"/api/projects/{pid}")


def test_clip_rename_and_delete_endpoints(client):
    import api
    import database

    r = client.post("/api/projects", json={"youtube_url": "https://youtu.be/clip-test"})
    pid = r.json()["project_id"]

    loop = asyncio.new_event_loop()
    clip = loop.run_until_complete(
        database.save_clip(pid, "/files/clip-test/x.mp4", 0, 30, title="orig")
    )
    loop.close()

    # rename
    r = client.patch(f"/api/clips/{clip['id']}", json={"title": "renamed!"})
    assert r.status_code == 200

    # list all clips
    r = client.get("/api/clips")
    assert r.status_code == 200
    assert any(c["id"] == clip["id"] for c in r.json())

    # 404s
    assert client.get("/api/clips/does-not-exist/download").status_code == 404
    assert client.patch("/api/clips/does-not-exist", json={"title": "x"}).status_code == 404

    # delete
    r = client.delete(f"/api/clips/{clip['id']}")
    assert r.status_code == 200 and r.json()["success"]

    client.delete(f"/api/projects/{pid}")


def test_project_404(client):
    assert client.get("/api/projects/nope").status_code == 404
    assert client.delete("/api/projects/nope").status_code == 404


def test_settings_roundtrip_and_key_never_returned(client):
    r = client.post(
        "/api/settings",
        json={
            "llm_provider": "ollama",
            "llm_api_key": "sk-test-123",
            "watermark_position": "top_right",
            "watermark_opacity": 0.5,
        },
    )
    assert r.status_code == 200

    r = client.get("/api/settings")
    data = r.json()
    assert data.get("llm_provider") == "ollama"
    assert data.get("watermark_position") == "top_right"
    # the raw key must never be returned
    assert "sk-test-123" not in json.dumps(data)
    assert data.get("has_api_key") is True


def test_auth_middleware_when_key_set(client, monkeypatch):
    import api

    monkeypatch.setattr(api, "_API_KEY", "sekret")
    try:
        assert client.get("/api/stats").status_code == 401
        r = client.get("/api/stats", headers={"X-API-Key": "sekret"})
        assert r.status_code == 200
        r = client.get("/api/stats", headers={"Authorization": "Bearer sekret"})
        assert r.status_code == 200
        # /files and /docs stay open
        assert client.get("/api/health").status_code == 401
    finally:
        monkeypatch.setattr(api, "_API_KEY", "")


def test_caption_styles_list(client):
    r = client.get("/api/caption-styles")
    assert r.status_code == 200
    styles = r.json()
    assert len(styles) >= 5
    assert all("key" in s and "name" in s for s in styles)
