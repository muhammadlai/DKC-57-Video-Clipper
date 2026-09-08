"""Permission registry + role mapping (authorization foundation).

Phase 1 keeps roles simple (``admin`` / ``user``). Permissions are explicit
strings seeded into the database so the UI can display them, while the
role→permission map lives in code where it is easy to audit. Later phases can
introduce per-user grants without changing the dependency API.
"""

from __future__ import annotations

import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from aitzaz_api.db.base import Base, TimestampMixin

# --- Permission codes ---------------------------------------------------------

PERM_CHAT_USE = "chat.use"
PERM_TASKS_CREATE = "tasks.create"
PERM_TASKS_MANAGE = "tasks.manage"
PERM_MEMORY_WRITE = "memory.write"
PERM_TOOLS_EXECUTE = "tools.execute"
PERM_TOOLS_MANAGE = "tools.manage"
PERM_APPROVALS_REQUEST = "approvals.request"
PERM_APPROVALS_DECIDE = "approvals.decide"
PERM_SETTINGS_WRITE = "settings.write"
PERM_ADMIN = "admin"

ALL_PERMISSIONS: list[dict[str, str]] = [
    {"code": PERM_CHAT_USE, "name": "Chat with agents"},
    {"code": PERM_TASKS_CREATE, "name": "Create tasks"},
    {"code": PERM_TASKS_MANAGE, "name": "Manage all tasks"},
    {"code": PERM_MEMORY_WRITE, "name": "Create and edit memories"},
    {"code": PERM_TOOLS_EXECUTE, "name": "Execute tools"},
    {"code": PERM_TOOLS_MANAGE, "name": "Enable/disable tools"},
    {"code": PERM_APPROVALS_REQUEST, "name": "Request approvals"},
    {"code": PERM_APPROVALS_DECIDE, "name": "Approve or reject requests"},
    {"code": PERM_SETTINGS_WRITE, "name": "Change settings"},
    {"code": PERM_ADMIN, "name": "Full administration"},
]

#: Sensible baseline for a personal (single-user) deployment.
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {p["code"] for p in ALL_PERMISSIONS},
    "user": {
        PERM_CHAT_USE,
        PERM_TASKS_CREATE,
        PERM_TASKS_MANAGE,
        PERM_MEMORY_WRITE,
        PERM_TOOLS_EXECUTE,
        PERM_APPROVALS_REQUEST,
        PERM_APPROVALS_DECIDE,
        PERM_SETTINGS_WRITE,
    },
}


def permissions_for_role(role: str) -> set[str]:
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["user"])


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
