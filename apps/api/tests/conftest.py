"""Pytest fixtures — isolated SQLite database + TestClient per session."""

from __future__ import annotations

import os
import tempfile

# Configure environment BEFORE the app (and its settings) are imported.
_TMP_DIR = tempfile.mkdtemp(prefix="aitzaz-tests-")
os.environ["AITZAZ_ENVIRONMENT"] = "development"
os.environ["AITZAZ_DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test.db"
os.environ["AITZAZ_AUTO_CREATE_TABLES"] = "true"
os.environ["AITZAZ_RATE_LIMIT_ENABLED"] = "false"
os.environ["AITZAZ_MOCK_LLM_DELAY_MS"] = "0"
os.environ["AITZAZ_SECRET_KEY"] = "test-secret-key-not-for-production-0123456789"
os.environ["AITZAZ_SEED_DEMO_USER"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from aitzaz_api.db.session import SessionLocal, engine  # noqa: E402
from aitzaz_api.main import app  # noqa: E402
from aitzaz_api.services.agent_service import ensure_builtin_agents  # noqa: E402
from aitzaz_api.services.tool_service import ensure_builtin_tools  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    import aitzaz_api.models  # noqa: F401
    from aitzaz_api.db.base import Base

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_builtin_tools(db)
        ensure_builtin_agents(db)
    finally:
        db.close()
    yield


@pytest.fixture(autouse=True)
def _clean_tables(_setup_database):
    yield
    # Wipe all data after each test for isolation.
    with engine.begin() as connection:
        for table in [
            "activity_logs",
            "approvals",
            "messages",
            "conversations",
            "memories",
            "tasks",
            "agent_configs",
            "agents",
            "tools",
            "settings",
            "sessions",
            "permissions",
            "users",
        ]:
            connection.execute(text(f"DELETE FROM {table}"))


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def register_and_login(client: TestClient, email="user@example.com", password="password-123", name="Test User"):
    """Helper: register a user, return auth headers + cookies handled client-side."""
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(client: TestClient, email="user@example.com", password="password-123"):
    """Login and return a Bearer header (cookie is set on the client too)."""
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
