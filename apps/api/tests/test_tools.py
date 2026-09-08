"""Tools API tests (list + execute + validation + auth)."""

from tests.conftest import register_and_login


def test_list_tools_includes_builtins(client):
    register_and_login(client)
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    slugs = {t["slug"] for t in response.json()}
    assert {"calculator", "current_time", "echo", "task_create", "memory_create", "approval_request"} <= slugs


def test_execute_calculator(client):
    register_and_login(client)
    response = client.post("/api/v1/tools/calculator/execute", json={"input": {"expression": "500 × 25"}})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["result"] == 12500
    assert body["duration_ms"] >= 0


def test_execute_calculator_division(client):
    register_and_login(client)
    response = client.post("/api/v1/tools/calculator/execute", json={"input": {"expression": "100 / 8"}})
    assert response.status_code == 200
    assert response.json()["result"]["result"] == 12.5


def test_execute_calculator_rejects_code_injection(client):
    """Code injection is never evaluated: the tool returns ok=false (never 500,
    never an executed result). Schema-level validation still returns 422."""
    register_and_login(client)
    response = client.post(
        "/api/v1/tools/calculator/execute", json={"input": {"expression": "__import__('os').system('id')"}}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "tool_invalid_input"
    assert body["error"]  # rejected without evaluation


def test_execute_tool_invalid_schema_input(client):
    register_and_login(client)
    response = client.post("/api/v1/tools/calculator/execute", json={"input": {"wrong": 1}})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]


def test_execute_unknown_tool_404(client):
    register_and_login(client)
    response = client.post("/api/v1/tools/nonexistent/execute", json={"input": {}})
    assert response.status_code == 404


def test_execute_echo(client):
    register_and_login(client)
    response = client.post("/api/v1/tools/echo/execute", json={"input": {"message": "ping"}})
    assert response.status_code == 200
    assert response.json()["result"]["message"] == "ping"


def test_execute_requires_auth(client):
    response = client.post("/api/v1/tools/echo/execute", json={"input": {"message": "x"}})
    assert response.status_code == 401
