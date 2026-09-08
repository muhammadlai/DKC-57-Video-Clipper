"""Approval workflow tests — REQUEST → DECIDE, double decisions, task links."""

from tests.conftest import register_and_login


def _create(client, **overrides):
    payload = {
        "action_type": "send_email",
        "description": "Send the contract to John",
        "payload": {"to": "john@example.com"},
        **overrides,
    }
    return client.post("/api/v1/approvals", json=payload)


def test_create_approval(client):
    register_and_login(client)
    response = _create(client)
    assert response.status_code == 201, response.text
    approval = response.json()
    assert approval["status"] == "pending"
    assert approval["action_type"] == "send_email"
    assert approval["decided_at"] is None
    assert approval["expires_at"] is not None


def test_invalid_action_type_rejected(client):
    register_and_login(client)
    response = _create(client, action_type="nuke_the_database")
    assert response.status_code == 422


def test_approve_flow(client):
    register_and_login(client)
    approval = _create(client).json()
    decision = client.post(
        f"/api/v1/approvals/{approval['id']}/decision", json={"decision": "approved"}
    )
    assert decision.status_code == 200
    body = decision.json()
    assert body["status"] == "approved"
    assert body["decided_at"] is not None


def test_reject_flow_with_note(client):
    register_and_login(client)
    approval = _create(client).json()
    decision = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "rejected", "note": "Not now"},
    )
    assert decision.json()["status"] == "rejected"
    assert decision.json()["decision_note"] == "Not now"


def test_double_decision_conflict(client):
    register_and_login(client)
    approval = _create(client).json()
    client.post(f"/api/v1/approvals/{approval['id']}/decision", json={"decision": "approved"})
    second = client.post(
        f"/api/v1/approvals/{approval['id']}/decision", json={"decision": "rejected"}
    )
    assert second.status_code == 409


def test_invalid_decision_value(client):
    register_and_login(client)
    approval = _create(client).json()
    response = client.post(
        f"/api/v1/approvals/{approval['id']}/decision", json={"decision": "maybe"}
    )
    assert response.status_code == 404


def test_approval_links_task_and_updates_status(client):
    register_and_login(client)
    task = client.post("/api/v1/tasks", json={"title": "Send invoices"}).json()
    approval = _create(client, task_id=task["id"]).json()

    updated_task = client.get(f"/api/v1/tasks/{task['id']}").json()
    assert updated_task["status"] == "waiting_approval"

    client.post(f"/api/v1/approvals/{approval['id']}/decision", json={"decision": "approved"})
    updated_task = client.get(f"/api/v1/tasks/{task['id']}").json()
    assert updated_task["status"] == "pending"


def test_rejected_request_cancels_linked_task(client):
    register_and_login(client)
    task = client.post("/api/v1/tasks", json={"title": "Buy domain"}).json()
    approval = _create(client, action_type="purchase", task_id=task["id"]).json()
    client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        json={"decision": "rejected", "note": "too expensive"},
    )
    updated_task = client.get(f"/api/v1/tasks/{task['id']}").json()
    assert updated_task["status"] == "cancelled"


def test_filter_by_status(client):
    register_and_login(client)
    _create(client)
    approved = _create(client, description="Another one")
    client.post(
        f"/api/v1/approvals/{approved.json()['id']}/decision", json={"decision": "rejected"}
    )
    pending = client.get("/api/v1/approvals", params={"status": "pending"}).json()
    assert pending["total"] == 1
    rejected = client.get("/api/v1/approvals", params={"status": "rejected"}).json()
    assert rejected["total"] == 1
