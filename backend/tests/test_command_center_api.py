import asyncio
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    import api

    with TestClient(api.app) as c:
        yield c


@pytest.fixture
def fake_state():
    return {
        "app": {"name": "AITZAZ AI", "subtitle": "LIVE CONTENT COMMAND CENTER"},
        "config": {
            "stumps_team_id": "-OiyGifAxdcSXcSbbE5m",
            "publish_mode": "approval",
            "auto_publish_minimum": 85,
            "pre_roll_seconds": 10,
            "post_roll_seconds": 15,
            "youtube_privacy_status": "private",
        },
        "youtube": {
            "configured": True,
            "connected": True,
            "channel_name": "Arena Test Channel",
            "channel_id": "abc",
            "live_active": True,
            "live": {"title": "Test Live", "url": "https://youtube.test/watch?v=123"},
            "source": {"ok": True, "stream_url": "https://stream.test/live.m3u8", "message": "Resolved"},
            "limitation": None,
        },
        "stumps": {
            "provider": "stumps",
            "team_id": "-OiyGifAxdcSXcSbbE5m",
            "connected": True,
            "live_data_available": True,
            "limitation": None,
            "match": {
                "match_id": "m1",
                "team_home": "Eagles",
                "team_away": "Titans",
                "score": "142",
                "wickets": "3",
                "overs": "18.4",
                "striker": "V. Kohli",
                "non_striker": "R. Sharma",
                "bowler": "S. Yadav",
                "recent_balls": ["1", "4", "6"],
                "event": "SIX",
                "timestamp": "2026-08-29T00:00:00Z",
            },
        },
        "ai_engine": {
            "online": True,
            "primary": "OpenAI",
            "fallback": "Gemini",
            "providers": {
                "openai": {"ok": True, "message": "verified"},
                "gemini": {"ok": True, "message": "verified"},
            },
            "message": "AI engine online",
        },
        "live_analysis": {"watching": True, "current_event": None},
        "moments": [],
        "publishing": {
            "mode": "approval",
            "jobs": [],
            "platforms": {
                "youtube": {"platform": "youtube", "ready": True, "state": "ok", "message": "ready"},
                "facebook": {"platform": "facebook", "ready": False, "state": "warn", "message": "not configured"},
                "tiktok": {"platform": "tiktok", "ready": False, "state": "warn", "message": "approval required"},
            },
        },
        "diagnostics": [
            {"key": "youtube_oauth", "label": "YouTube OAuth", "state": "ok", "message": "Connected", "required_for_start": True}
        ],
        "production": {"active": False, "can_start": True, "blockers": []},
        "buffer": {"running": True, "ready": True, "segment_count": 3, "latest_segment_end": 1000.0, "source_url": "https://stream.test/live.m3u8"},
        "refreshed_at": "2026-08-29T00:00:00Z",
        "refreshed_at_ts": 1000.0,
    }


def test_command_center_state_route(client, monkeypatch, fake_state):
    import api

    async def fake_refresh(force: bool = False):
        return fake_state

    monkeypatch.setattr(api.command_center, "refresh", fake_refresh)
    r = client.get("/api/command-center/state")
    assert r.status_code == 200
    body = r.json()
    assert body["app"]["name"] == "AITZAZ AI"
    assert body["youtube"]["connected"] is True
    assert body["stumps"]["match"]["striker"] == "V. Kohli"


def test_youtube_oauth_start_and_callback(client, monkeypatch):
    import api
    import youtube_oauth

    monkeypatch.setattr(youtube_oauth, "oauth_configured", lambda: True)
    monkeypatch.setattr(youtube_oauth, "new_state", lambda: "state-123")
    monkeypatch.setattr(youtube_oauth, "build_auth_url", lambda state: f"https://accounts.google.com/o/oauth2/v2/auth?state={state}")

    exchanged = []

    async def fake_exchange(code: str):
        exchanged.append(code)
        return {"access_token": "tok"}

    monkeypatch.setattr(youtube_oauth, "exchange_code", fake_exchange)

    r = client.post("/api/youtube/auth/start")
    assert r.status_code == 200
    assert "state=state-123" in r.json()["auth_url"]

    r = client.get("/api/youtube/auth/callback?code=abc&state=state-123", follow_redirects=False)
    assert r.status_code in {302, 307}
    assert exchanged == ["abc"]


def test_admin_unlock_lock_and_masked_config(client, monkeypatch):
    import admin_security

    monkeypatch.setenv("ADMIN_UNLOCK_CODE", "893955")
    os.environ["OPENAI_API_KEY"] = "real-openai-secret"
    os.environ["GEMINI_API_KEY"] = "real-gemini-secret"

    wrong = client.post("/api/admin/unlock", json={"code": "000000"})
    assert wrong.status_code == 401

    ok = client.post("/api/admin/unlock", json={"code": "893955"})
    assert ok.status_code == 200
    assert ok.json()["active"] is True

    cfg = client.get("/api/admin/config")
    assert cfg.status_code == 200
    body = cfg.json()
    assert body["secrets"]["openai"] == "••••••••••••"
    assert body["secrets"]["gemini"] == "••••••••••••"
    assert "real-openai-secret" not in str(body)
    assert "real-gemini-secret" not in str(body)

    locked = client.post("/api/admin/lock")
    assert locked.status_code == 200
    assert locked.json()["active"] is False

    unauthorized = client.get("/api/admin/config")
    assert unauthorized.status_code == 401


def test_start_stop_production_requires_admin_and_uses_service(client, monkeypatch, fake_state):
    import api

    monkeypatch.setenv("ADMIN_UNLOCK_CODE", "893955")

    async def fake_start():
        new_state = dict(fake_state)
        new_state["production"] = {"active": True, "can_start": True, "blockers": []}
        return new_state

    async def fake_stop():
        return fake_state

    monkeypatch.setattr(api.command_center, "start_production", fake_start)
    monkeypatch.setattr(api.command_center, "stop_production", fake_stop)

    unauth = client.post("/api/production/start")
    assert unauth.status_code == 401

    client.post("/api/admin/unlock", json={"code": "893955"})
    started = client.post("/api/production/start")
    assert started.status_code == 200
    assert started.json()["production"]["active"] is True

    stopped = client.post("/api/production/stop")
    assert stopped.status_code == 200
    assert stopped.json()["production"]["active"] is False


def test_health_reports_new_backend_flags(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "AITZAZ AI"
    assert "youtube_oauth_configured" in body
    assert "admin_code_configured" in body
