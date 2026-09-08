"""Authentication flow tests: register, login, me, logout, protection."""

from tests.conftest import auth_headers, register_and_login


def test_register_success(client):
    body = register_and_login(client, email="alice@example.com", name="Alice")
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == "admin"
    assert body["token_type"] == "bearer"
    assert "access_token" in body


def test_register_duplicate_email_conflict(client):
    register_and_login(client, email="bob@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Bob Again", "email": "bob@example.com", "password": "password-123"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_short_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Bob", "email": "bob2@example.com", "password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_login_success_sets_cookie(client):
    register_and_login(client, email="carol@example.com")
    response = client.post(
        "/api/v1/auth/login", json={"email": "carol@example.com", "password": "password-123"}
    )
    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "aitzaz_session=" in set_cookie
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()


def test_login_wrong_password_unauthorized(client):
    register_and_login(client, email="dave@example.com")
    response = client.post(
        "/api/v1/auth/login", json={"email": "dave@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_with_token(client):
    register_and_login(client, email="erin@example.com")
    headers = auth_headers(client, email="erin@example.com")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "erin@example.com"


def test_me_with_cookie(client):
    register_and_login(client, email="frank@example.com")
    # TestClient stores the session cookie automatically.
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "frank@example.com"


def test_logout_revokes_session(client):
    register_and_login(client, email="grace@example.com")
    assert client.get("/api/v1/auth/me").status_code == 200
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    # Old cookie/session must no longer authenticate.
    assert client.get("/api/v1/auth/me").status_code == 401


def test_garbage_token_unauthorized(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_update_profile(client):
    register_and_login(client, email="henry@example.com")
    response = client.patch("/api/v1/auth/me", json={"name": "Henry Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Henry Updated"
