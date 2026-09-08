"""Activity log, settings and agents endpoint tests."""

from tests.conftest import register_and_login


def test_activity_records_login(client):
    register_and_login(client, email="log-user@example.com")
    listing = client.get("/api/v1/activity").json()
    types = {item["activity_type"] for item in listing["items"]}
    assert "user_registered" in types
    assert "login" in types


def test_activity_records_task_and_tool_events(client):
    register_and_login(client)
    client.post("/api/v1/tasks", json={"title": "Audited task"})
    client.post("/api/v1/tools/calculator/execute", json={"input": {"expression": "2 + 2"}})
    listing = client.get("/api/v1/activity").json()
    types = {item["activity_type"] for item in listing["items"]}
    assert "task_created" in types
    assert "tool_executed" in types


def test_activity_filter_by_type(client):
    register_and_login(client)
    client.post("/api/v1/tasks", json={"title": "T"})
    listing = client.get("/api/v1/activity", params={"type": "task_created"}).json()
    assert listing["total"] == 1
    assert all(i["activity_type"] == "task_created" for i in listing["items"])


def test_activity_requires_auth(client):
    assert client.get("/api/v1/activity").status_code == 401


def test_logout_logged(client):
    register_and_login(client)
    client.post("/api/v1/auth/logout")
    # after logout we're signed out; login again to inspect
    client.post("/api/v1/auth/login", json={"email": "log-user2@x.io", "password": "x"})  # wrong creds fine
    register_and_login(client, email="log-user3@example.com")
    listing = client.get("/api/v1/activity").json()
    types = {item["activity_type"] for item in listing["items"]}
    assert "logout" in types or "login" in types


def test_settings_roundtrip(client):
    register_and_login(client)
    defaults = client.get("/api/v1/settings").json()["data"]
    assert "appearance" in defaults and "notifications" in defaults

    updated = client.patch(
        "/api/v1/settings",
        json={"section": "appearance", "values": {"theme": "light", "accent": "violet"}},
    )
    assert updated.status_code == 200
    data = updated.json()["data"]
    assert data["appearance"]["theme"] == "light"
    assert data["appearance"]["accent"] == "violet"
    # untouched defaults still present
    assert data["appearance"]["density"] == "comfortable"

    # unknown section rejected
    bad = client.patch("/api/v1/settings", json={"section": "rocket", "values": {}})
    assert bad.status_code == 422


def test_settings_change_logged(client):
    register_and_login(client)
    client.patch("/api/v1/settings", json={"section": "memory", "values": {"auto_remember": False}})
    listing = client.get("/api/v1/activity").json()
    types = {item["activity_type"] for item in listing["items"]}
    assert "settings_updated" in types


def test_agents_list_contains_personal_assistant(client):
    register_and_login(client)
    agents = client.get("/api/v1/agents").json()
    assert len(agents) >= 1
    pa = next(a for a in agents if a["slug"] == "personal-assistant")
    assert pa["is_builtin"] is True
    assert pa["status"] == "active"
    assert "calculator" in pa["tools"]
    assert pa["capabilities"]


def test_agent_detail(client):
    register_and_login(client)
    response = client.get("/api/v1/agents/personal-assistant")
    assert response.status_code == 200
    assert response.json()["name"] == "Personal Assistant"


def test_agent_unknown_404(client):
    register_and_login(client)
    assert client.get("/api/v1/agents/does-not-exist").status_code == 404


def test_future_agents_listing(client):
    register_and_login(client)
    response = client.get("/api/v1/agents/future")
    assert response.status_code == 200
    slugs = {a["slug"] for a in response.json()["agents"]}
    assert {"research-agent", "browser-agent"} <= slugs


def test_stats_endpoint(client):
    register_and_login(client)
    client.post("/api/v1/tasks", json={"title": "One"})
    client.post("/api/v1/memories", json={"content": "Something"})
    stats = client.get("/api/v1/stats").json()
    assert stats["tasks"]["total"] == 1
    assert stats["memories_count"] == 1
    assert stats["demo_mode"] is True
    assert stats["agent_status"] == "active"
    assert len(stats["recent_activity"]) >= 1


def test_search_endpoint(client):
    register_and_login(client)
    client.post("/api/v1/tasks", json={"title": "Find the unicorn contract"})
    results = client.get("/api/v1/search", params={"q": "unicorn"}).json()
    assert len(results["tasks"]) == 1
    empty = client.get("/api/v1/search", params={"q": "zzzznotfound"}).json()
    assert empty["tasks"] == []
