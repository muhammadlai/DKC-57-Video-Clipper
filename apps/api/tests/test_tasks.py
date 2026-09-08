"""Task CRUD + transition tests."""

from tests.conftest import register_and_login


def test_create_and_get_task(client):
    register_and_login(client)
    created = client.post(
        "/api/v1/tasks",
        json={"title": "Prepare report", "description": "Quarterly numbers", "priority": "high"},
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["status"] == "pending"
    assert task["priority"] == "high"

    fetched = client.get(f"/api/v1/tasks/{task['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Prepare report"


def test_task_defaults(client):
    register_and_login(client)
    task = client.post("/api/v1/tasks", json={"title": "Simple"}).json()
    assert task["status"] == "pending"
    assert task["priority"] == "medium"
    assert task["due_at"] is None


def test_task_priority_validation(client):
    register_and_login(client)
    response = client.post("/api/v1/tasks", json={"title": "X", "priority": "mega"})
    assert response.status_code == 422


def test_list_and_filter_tasks(client):
    register_and_login(client)
    client.post("/api/v1/tasks", json={"title": "A"})
    client.post("/api/v1/tasks", json={"title": "B", "priority": "low"})
    listing = client.get("/api/v1/tasks").json()
    assert listing["total"] == 2

    listing = client.get("/api/v1/tasks", params={"priority": "low"}).json()
    assert listing["total"] == 1
    assert listing["items"][0]["title"] == "B"


def test_status_transitions(client):
    register_and_login(client)
    task = client.post("/api/v1/tasks", json={"title": "Flow"}).json()
    tid = task["id"]

    # pending → running → completed (legal)
    response = client.patch(f"/api/v1/tasks/{tid}", json={"status": "running"})
    assert response.json()["status"] == "running"
    response = client.patch(f"/api/v1/tasks/{tid}", json={"status": "completed"})
    assert response.json()["status"] == "completed"

    # completed is final
    response = client.patch(f"/api/v1/tasks/{tid}", json={"status": "pending"})
    assert response.status_code == 409
    assert "Cannot change task status" in response.json()["error"]["message"]


def test_invalid_status_rejected(client):
    register_and_login(client)
    task = client.post("/api/v1/tasks", json={"title": "X"}).json()
    response = client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "warp-speed"})
    assert response.status_code == 422


def test_update_and_delete_task(client):
    register_and_login(client)
    task = client.post("/api/v1/tasks", json={"title": "Before"}).json()
    updated = client.patch(f"/api/v1/tasks/{task['id']}", json={"title": "After", "description": "Updated"})
    assert updated.json()["title"] == "After"

    deleted = client.delete(f"/api/v1/tasks/{task['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/tasks/{task['id']}").status_code == 404


def test_task_isolation_between_users(client):
    register_and_login(client, email="user1@example.com")
    task = client.post("/api/v1/tasks", json={"title": "Mine"}).json()

    client.post("/api/v1/auth/logout")
    register_and_login(client, email="user2@example.com")
    response = client.get(f"/api/v1/tasks/{task['id']}")
    assert response.status_code == 404  # cannot see other users' tasks


def test_task_stats(client):
    register_and_login(client)
    client.post("/api/v1/tasks", json={"title": "One"})
    client.post("/api/v1/tasks", json={"title": "Two"})
    stats = client.get("/api/v1/tasks/stats").json()
    assert stats["total"] == 2
    assert stats["pending"] == 2
