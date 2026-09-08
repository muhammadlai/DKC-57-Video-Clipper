"""Health endpoint tests."""


def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "Aitzaz AI"
    assert body["components"]["database"]["status"] == "ok"
    assert body["components"]["llm"]["provider"] == "mock-demo"


def test_health_v1_alias(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_info(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_openapi_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for expected in [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/me",
        "/api/v1/chat",
        "/api/v1/agents",
        "/api/v1/tools",
        "/api/v1/tools/{slug}/execute",
        "/api/v1/memories",
        "/api/v1/tasks",
        "/api/v1/approvals",
        "/api/v1/approvals/{approval_id}/decision",
        "/api/v1/activity",
        "/api/v1/settings",
        "/api/v1/stats",
    ]:
        assert expected in paths, f"missing endpoint {expected}"
