"""Tool service — bridges the code-level ToolRegistry with the database.

``ensure_builtin_tools`` mirrors the code registry into the ``tools`` table
(idempotent), so the UI/API always has real rows with schemas, and ``execute``
runs the same validation + permission + audit path for both the Tools page
(actor="user") and the agent (actor="agent").
"""

from __future__ import annotations

import logging
from typing import Any

from aitzaz_tools import (
    ToolContext,
    ToolError,
    ToolRegistry,
    ToolResult,
    build_demo_tools,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from aitzaz_api.agent_tools import build_agent_tools
from aitzaz_api.core.errors import AppError, ForbiddenError
from aitzaz_api.models.activity import ActivityType
from aitzaz_api.models.permission import permissions_for_role
from aitzaz_api.models.tool import Tool
from aitzaz_api.models.user import User
from aitzaz_api.services.activity_service import log_activity

logger = logging.getLogger("aitzaz.tools")

_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Process-wide registry of executable tools (code level)."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        for tool in [*build_demo_tools(), *build_agent_tools()]:
            _registry.register(tool, replace=True)
    return _registry


def ensure_builtin_tools(db: Session) -> None:
    """Idempotently sync code tools into the tools table."""
    for tool in get_registry().list_tools():
        row = db.scalar(select(Tool).where(Tool.slug == tool.slug))
        spec = tool.spec()
        if row is None:
            db.add(
                Tool(
                    slug=spec["slug"],
                    name=spec["name"],
                    description=spec["description"],
                    category=spec["category"],
                    input_schema=spec["input_schema"],
                    output_schema=spec["output_schema"],
                    required_permission=spec["required_permission"],
                    execution="local",
                    enabled=True,
                    is_builtin=True,
                )
            )
        else:
            row.name = spec["name"]
            row.description = spec["description"]
            row.category = spec["category"]
            row.input_schema = spec["input_schema"]
            row.output_schema = spec["output_schema"]
            row.required_permission = spec["required_permission"]
            row.is_builtin = True
    db.commit()


def list_tools(db: Session) -> list[Tool]:
    return list(db.scalars(select(Tool).order_by(Tool.category, Tool.slug)).all())


def get_tool_row(db: Session, slug: str) -> Tool | None:
    return db.scalar(select(Tool).where(Tool.slug == slug))


def _permission_checker(user: User):
    granted = permissions_for_role(user.role)

    def checker(permission: str) -> None:
        if permission not in granted:
            raise ForbiddenError(
                f"Your role '{user.role}' lacks the '{permission}' permission required for this tool"
            )

    return checker


def execute_tool(
    db: Session,
    *,
    user: User,
    slug: str,
    input_data: dict[str, Any] | None,
    actor: str = "user",
    ip: str | None = None,
    config: dict[str, Any] | None = None,
    commit: bool = True,
) -> ToolResult:
    """Validate → execute → audit. Raises ToolError subclasses on failure."""
    row = get_tool_row(db, slug)
    if row is None:
        from aitzaz_tools.base import ToolNotFoundError

        raise ToolNotFoundError(f"Unknown tool: '{slug}'")
    if not row.enabled:
        from aitzaz_tools.base import ToolDisabledError

        raise ToolDisabledError(f"Tool '{slug}' is disabled")

    ctx = ToolContext(
        user_id=str(user.id),
        actor=actor,
        config={**(config or {}), "default_timezone": _default_timezone()},
    )
    result = get_registry().execute(
        slug, input_data, ctx, permission_checker=_permission_checker(user)
    )

    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.TOOL_EXECUTED,
        message=(
            f"Tool '{slug}' executed by {actor}: {'ok' if result.ok else 'failed'}"
            f" ({result.duration_ms} ms)"
        ),
        meta={
            "tool": slug,
            "ok": result.ok,
            "error": result.error,
            "actor": actor,
            "duration_ms": result.duration_ms,
        },
        ip=ip,
    )
    if commit:
        db.commit()
    return result


def _default_timezone() -> str:
    from aitzaz_api.core.config import get_settings

    try:
        return get_settings().default_timezone
    except Exception:  # noqa: BLE001
        return "UTC"


def tool_error_to_http(exc: ToolError) -> AppError:
    """Map ToolError families onto the API error envelope."""
    from aitzaz_tools.base import (
        ToolDisabledError,
        ToolInputError,
        ToolNotFoundError,
        ToolPermissionError,
    )

    if isinstance(exc, ToolNotFoundError):
        return AppError(exc.message, code="not_found", status_code=404)
    if isinstance(exc, ToolDisabledError):
        return AppError(exc.message, code="tool_disabled", status_code=409)
    if isinstance(exc, ToolPermissionError):
        return ForbiddenError(exc.message)
    if isinstance(exc, ToolInputError):
        return AppError(exc.message, code="validation_error", status_code=422, details=exc.details)
    return AppError(exc.message, code="tool_error", status_code=400, details=exc.details)
