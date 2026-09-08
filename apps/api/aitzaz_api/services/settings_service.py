"""User settings service — defaults merged with stored overrides."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from aitzaz_api.core.config import Settings, get_settings
from aitzaz_api.models.activity import ActivityType
from aitzaz_api.models.settings import UserSetting
from aitzaz_api.models.user import User
from aitzaz_api.services.activity_service import log_activity

SECTION_NAMES = [
    "general",
    "ai_provider",
    "appearance",
    "security",
    "notifications",
    "memory",
    "tools",
    "permissions",
]


def default_settings(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return {
        "general": {"language": "en", "timezone": settings.default_timezone},
        "ai_provider": {
            "provider": settings.llm_provider,
            "demo_mode": settings.llm_provider == "mock",
            "note": "Real provider configuration UI arrives in Phase 2",
        },
        "appearance": {"theme": "dark", "accent": "indigo", "density": "comfortable"},
        "security": {
            "mfa": False,
            "session_timeout_minutes": settings.access_token_expire_minutes,
            "note": "MFA arrives in Phase 12",
        },
        "notifications": {
            "in_app": True,
            "email": False,
            "desktop": False,
            "approval_alerts": True,
            "note": "Delivery channels arrive in later phases",
        },
        "memory": {
            "auto_remember": True,
            "memory_in_chat": True,
            "note": "Semantic/vector memory arrives in Phase 3",
        },
        "tools": {
            "allow_agent_auto_execute": True,
            "require_approval_for_tools": False,
        },
        "permissions": {},
    }


def _get_row(db: Session, user: User) -> UserSetting:
    row = db.scalar(select(UserSetting).where(UserSetting.user_id == user.id))
    if row is None:
        row = UserSetting(user_id=user.id, data={})
        db.add(row)
        db.flush()
    return row


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = {**base}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def get_user_settings(db: Session, *, user: User) -> dict[str, Any]:
    settings = get_settings()
    row = _get_row(db, user)
    merged = _deep_merge(default_settings(settings), row.data or {})
    # Runtime truth for the AI provider section (cannot be overridden client-side).
    merged["ai_provider"]["provider"] = settings.llm_provider
    merged["ai_provider"]["demo_mode"] = settings.llm_provider == "mock"
    return merged


def update_section(
    db: Session,
    *,
    user: User,
    section: str,
    values: dict[str, Any],
    ip: str | None = None,
) -> dict[str, Any]:
    if section not in SECTION_NAMES:
        from aitzaz_api.core.errors import NotFoundError

        raise NotFoundError(f"Unknown settings section '{section}'")
    if not isinstance(values, dict):
        from aitzaz_api.core.errors import BadRequestError

        raise BadRequestError("values must be an object")

    row = _get_row(db, user)
    stored = dict(row.data or {})
    stored[section] = _deep_merge(stored.get(section, {}), values)
    row.data = stored
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.SETTINGS_UPDATED,
        message=f"Settings updated: {section}",
        meta={"section": section, "keys": sorted(values.keys())},
        ip=ip,
    )
    db.commit()
    return get_user_settings(db, user=user)
