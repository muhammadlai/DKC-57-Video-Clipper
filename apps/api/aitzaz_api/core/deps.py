"""FastAPI dependencies — auth, permissions, client info."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from aitzaz_api.core.config import Settings, get_settings
from aitzaz_api.core.errors import ForbiddenError, UnauthorizedError
from aitzaz_api.db.session import get_db
from aitzaz_api.models.permission import permissions_for_role
from aitzaz_api.models.user import User
from aitzaz_api.services.auth_service import resolve_token


def get_current_settings() -> Settings:
    return get_settings()


DbSession = Annotated[Session, Depends(get_db)]


def get_token(request: Request) -> str | None:
    """Token from the httpOnly cookie, falling back to Authorization header."""
    cookie_token = request.cookies.get(get_settings().cookie_name)
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(get_token)],
) -> User:
    if not token:
        raise UnauthorizedError("Authentication required. Please sign in.")
    user, _session = resolve_token(db, token)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission_code: str):
    """Authorization foundation — role → permission check."""

    def dependency(user: CurrentUser) -> User:
        granted = permissions_for_role(user.role)
        if permission_code not in granted:
            raise ForbiddenError(
                f"Missing required permission: '{permission_code}' (role: {user.role})"
            )
        return user

    return Depends(dependency)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")
