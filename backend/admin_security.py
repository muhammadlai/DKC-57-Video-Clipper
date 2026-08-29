"""
admin_security.py — backend-verified administrator lock for AITZAZ AI.

Implements rate limiting, failed-login lockout, signed session expiry,
and helper functions for FastAPI routes.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any, Optional

from fastapi import HTTPException  # type: ignore


ATTEMPTS_LIMIT = int(os.getenv("ADMIN_MAX_ATTEMPTS", "5"))
LOCKOUT_MINUTES = int(os.getenv("ADMIN_LOCKOUT_MINUTES", "10"))
SESSION_MINUTES = int(os.getenv("ADMIN_SESSION_MINUTES", "30"))

_failures: dict[str, dict[str, Any]] = {}


def admin_code() -> str:
    return os.getenv("ADMIN_UNLOCK_CODE", "").strip()


def is_configured() -> bool:
    return bool(admin_code())


def unlock(session: dict[str, Any], ip: str, submitted_code: str) -> tuple[bool, str]:
    now = dt.datetime.now(dt.timezone.utc)
    state = _failures.get(ip) or {"count": 0, "locked_until": None}
    locked_until = _parse_dt(state.get("locked_until"))
    if locked_until and locked_until > now:
        remaining = int((locked_until - now).total_seconds() // 60) + 1
        return False, f"Admin login is temporarily locked. Try again in about {remaining} minute(s)."

    expected = admin_code()
    if not expected:
        return False, "ADMIN_UNLOCK_CODE is not configured on the backend."

    if submitted_code != expected:
        count = int(state.get("count") or 0) + 1
        record: dict[str, Any] = {"count": count, "locked_until": None}
        if count >= ATTEMPTS_LIMIT:
            record["locked_until"] = (now + dt.timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            record["count"] = 0
        _failures[ip] = record
        if record.get("locked_until"):
            return False, f"Too many failed attempts. Admin login is locked for {LOCKOUT_MINUTES} minutes."
        remaining = ATTEMPTS_LIMIT - count
        return False, f"Invalid unlock code. {remaining} attempt(s) remaining before lockout."

    _failures.pop(ip, None)
    expires_at = now + dt.timedelta(minutes=SESSION_MINUTES)
    session["admin_authenticated"] = True
    session["admin_expires_at"] = expires_at.isoformat()
    return True, "ADMIN MODE ACTIVE"


def lock(session: dict[str, Any]) -> None:
    session.pop("admin_authenticated", None)
    session.pop("admin_expires_at", None)


def session_status(session: dict[str, Any]) -> dict[str, Any]:
    active = is_session_active(session)
    return {
        "configured": is_configured(),
        "active": active,
        "expires_at": session.get("admin_expires_at") if active else None,
    }


def is_session_active(session: dict[str, Any]) -> bool:
    if not session.get("admin_authenticated"):
        return False
    expires = _parse_dt(session.get("admin_expires_at"))
    if not expires or expires <= dt.datetime.now(dt.timezone.utc):
        lock(session)
        return False
    return True


def require_admin(session: dict[str, Any]) -> None:
    if not is_session_active(session):
        raise HTTPException(status_code=401, detail="Admin authentication required")


def _parse_dt(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except Exception:
        return None
