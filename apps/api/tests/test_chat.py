"""Chat + agent pipeline tests."""

from tests.conftest import register_and_login


def test_chat_hello_demo_ai(client):
    register_and_login(client)
    response = client.post("/api/v1/chat", json={"message": "Hello Aitzaz"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["demo_mode"] is True
    assert body["provider"] == "mock-demo"
    assert "Demo AI" in body["assistant_message"]["content"] or "demo" in body["assistant_message"]["content"].lower()
    assert body["assistant_message"]["role"] == "assistant"
    assert body["user_message"]["role"] == "user"


def test_chat_calculator_tool_call(client):
    register_and_login(client)
    response = client.post("/api/v1/chat", json={"message": "Calculate 125 × 48"})
    assert response.status_code == 200
    body = response.json()
    slugs = [call["slug"] for call in body["tool_calls"]]
    assert "calculator" in slugs
    calc = next(call for call in body["tool_calls"] if call["slug"] == "calculator")
    assert calc["ok"] is True
    assert calc["result"]["result"] == 6000
    assert "6,000" in body["assistant_message"]["content"]


def test_chat_current_time_tool(client):
    register_and_login(client)
    response = client.post("/api/v1/chat", json={"message": "What time is it?"})
    assert response.status_code == 200
    slugs = [call["slug"] for call in response.json()["tool_calls"]]
    assert "current_time" in slugs


def test_chat_creates_task_via_agent(client):
    register_and_login(client)
    response = client.post("/api/v1/chat", json={"message": "Remind me to call the bank tomorrow"})
    assert response.status_code == 200
    body = response.json()
    slugs = [call["slug"] for call in body["tool_calls"]]
    assert "task_create" in slugs
    # The task really exists:
    tasks = client.get("/api/v1/tasks").json()
    assert tasks["total"] == 1
    assert "bank" in tasks["items"][0]["title"].lower()


def test_chat_creates_approval_for_sensitive_action(client):
    register_and_login(client)
    response = client.post("/api/v1/chat", json={"message": "Send an email to John about the contract"})
    assert response.status_code == 200
    slugs = [call["slug"] for call in response.json()["tool_calls"]]
    assert "approval_request" in slugs
    approvals = client.get("/api/v1/approvals").json()
    assert approvals["total"] == 1
    assert approvals["items"][0]["status"] == "pending"
    assert approvals["items"][0]["action_type"] == "send_email"


def test_chat_creates_memory_via_agent(client):
    register_and_login(client)
    response = client.post(
        "/api/v1/chat", json={"message": "Remember that I prefer concise reports"}
    )
    assert response.status_code == 200
    slugs = [call["slug"] for call in response.json()["tool_calls"]]
    assert "memory_create" in slugs
    memories = client.get("/api/v1/memories").json()
    assert memories["total"] == 1
    assert "concise" in memories["items"][0]["content"]


def test_conversation_history_persists(client):
    register_and_login(client)
    first = client.post("/api/v1/chat", json={"message": "Hello Aitzaz"}).json()
    conversation_id = first["conversation_id"]
    client.post("/api/v1/chat", json={"message": "What time is it?", "conversation_id": conversation_id})
    messages = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages").json()
    assert len(messages) == 4  # 2 exchanges
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_conversation_list(client):
    register_and_login(client)
    client.post("/api/v1/chat", json={"message": "Hello"})
    conversations = client.get("/api/v1/chat/conversations").json()
    assert len(conversations) == 1
    assert conversations[0]["message_count"] == 2


def test_clear_conversation(client):
    register_and_login(client)
    first = client.post("/api/v1/chat", json={"message": "Hello"}).json()
    conversation_id = str(first["conversation_id"])
    response = client.delete(f"/api/v1/chat/conversations/{conversation_id}")
    assert response.status_code == 200
    assert client.get("/api/v1/chat/conversations").json() == []
    response = client.get(f"/api/v1/chat/conversations/{conversation_id}/messages")
    assert response.status_code == 404


def test_chat_requires_auth(client):
    response = client.post("/api/v1/chat", json={"message": "hi"})
    assert response.status_code == 401


def test_chat_empty_message_rejected(client):
    register_and_login(client)
    response = client.post("/api/v1/chat", json={"message": "   "})
    assert response.status_code == 422 or response.status_code == 400
