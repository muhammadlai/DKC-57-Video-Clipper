"""Memory CRUD tests."""

from tests.conftest import register_and_login


def test_create_and_list_memories(client):
    register_and_login(client)
    created = client.post(
        "/api/v1/memories",
        json={"content": "I live in Lahore", "category": "fact", "importance": 5},
    )
    assert created.status_code == 201, created.text
    memory = created.json()
    assert memory["category"] == "fact"
    assert memory["importance"] == 5

    listing = client.get("/api/v1/memories").json()
    assert listing["total"] == 1
    assert listing["items"][0]["content"] == "I live in Lahore"


def test_memory_category_normalization(client):
    register_and_login(client)
    memory = client.post(
        "/api/v1/memories", json={"content": "Prefer short answers", "category": "PREFERENCE"}
    ).json()
    assert memory["category"] == "preference"


def test_memory_unknown_category_falls_back(client):
    register_and_login(client)
    memory = client.post(
        "/api/v1/memories", json={"content": "Some note", "category": "nonsense"}
    ).json()
    assert memory["category"] == "fact"


def test_memory_importance_bounds(client):
    register_and_login(client)
    response = client.post("/api/v1/memories", json={"content": "X", "importance": 9})
    assert response.status_code == 422


def test_memory_search(client):
    register_and_login(client)
    client.post("/api/v1/memories", json={"content": "Prefers dark mode"})
    client.post("/api/v1/memories", json={"content": "Birthday is March 3"})
    listing = client.get("/api/v1/memories", params={"search": "dark"}).json()
    assert listing["total"] == 1
    assert "dark" in listing["items"][0]["content"]


def test_update_and_delete_memory(client):
    register_and_login(client)
    memory = client.post("/api/v1/memories", json={"content": "Before"}).json()
    updated = client.patch(
        f"/api/v1/memories/{memory['id']}", json={"content": "After", "importance": 5}
    )
    assert updated.json()["content"] == "After"
    assert updated.json()["importance"] == 5

    deleted = client.delete(f"/api/v1/memories/{memory['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/memories/{memory['id']}").status_code == 404
