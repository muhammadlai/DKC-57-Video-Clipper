"""Authentication service — registration, login, logout, sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aitzaz_api.core.config import Settings, get_settings
from aitzaz_api.core.errors import ConflictError, UnauthorizedError
from aitzaz_api.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from aitzaz_api.models.activity import ActivityType
from aitzaz_api.models.session import AuthSession
from aitzaz_api.models.settings import UserSetting
from aitzaz_api.models.user import User
from aitzaz_api.services.activity_service import log_activity


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


def get_user_by_id(db: Session, user_id: UUID | str) -> User | None:
    return db.get(User, UUID(str(user_id)))


def register_user(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
    settings: Settings | None = None,
) -> tuple[User, str, datetime]:
    settings = settings or get_settings()
    normalized = _normalize_email(email)
    if get_user_by_email(db, normalized) is not None:
        raise ConflictError("An account with this email already exists")

    user = User(
        name=name.strip(),
        email=normalized,
        hashed_password=hash_password(password, rounds=settings.bcrypt_rounds),
        role="admin",  # personal deployment: first accounts manage their own agent
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(UserSetting(user_id=user.id, data={}))

    token, jti, expires_at = create_access_token(
        subject=str(user.id),
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_expire_minutes,
    )
    db.add(
        AuthSession(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            ip=ip,
            user_agent=(user_agent or "")[:400] or None,
        )
    )
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.REGISTERED,
        message=f"Account registered ({normalized})",
        ip=ip,
    )
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.LOGIN,
        message=f"Signed in ({normalized})",
        meta={"first_login": True},
        ip=ip,
    )
    db.commit()
    db.refresh(user)
    return user, token, expires_at


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
    settings: Settings | None = None,
) -> tuple[User, str, datetime]:
    settings = settings or get_settings()
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled")

    user.last_login_at = datetime.now(UTC)

    token, jti, expires_at = create_access_token(
        subject=str(user.id),
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_expire_minutes,
    )
    db.add(
        AuthSession(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
            ip=ip,
            user_agent=(user_agent or "")[:400] or None,
        )
    )
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.LOGIN,
        message=f"Signed in ({normalized_email(user.email)})",
        ip=ip,
    )
    db.commit()
    db.refresh(user)
    return user, token, expires_at


def normalized_email(email: str) -> str:  # pragma: no cover — tiny helper
    return email.strip().lower()


def logout_user(db: Session, *, user: User, jti: str, ip: str | None = None) -> None:
    from datetime import datetime as _dt

    session_row = db.scalar(select(AuthSession).where(AuthSession.jti == jti))
    if session_row and session_row.revoked_at is None:
        session_row.revoked_at = _dt.now(UTC)
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.LOGOUT,
        message="Signed out",
        ip=ip,
    )
    db.commit()


def resolve_token(db: Session, token: str, *, settings: Settings | None = None) -> tuple[User, AuthSession]:
    """Decode a token and resolve it to an active user + live session row."""
    settings = settings or get_settings()
    from aitzaz_api.core.security import TokenError

    try:
        payload = decode_token(token, secret_key=settings.secret_key, algorithm=settings.jwt_algorithm)
    except TokenError as exc:
        raise UnauthorizedError(str(exc) or "Invalid or expired session") from exc
    jti = payload["jti"]

    session_row = db.scalar(select(AuthSession).where(AuthSession.jti == jti))
    if session_row is None:
        raise UnauthorizedError("Session not found. Please sign in again.")
    from datetime import datetime as _dt

    now = _dt.now(UTC)
    if session_row.revoked_at is not None:
        raise UnauthorizedError("Session was revoked. Please sign in again.")
    expires_at = session_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < now:
        raise UnauthorizedError("Session expired. Please sign in again.")

    user = db.get(User, session_row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is unavailable")
    return user, session_row


def update_profile(db: Session, *, user: User, name: str, ip: str | None = None) -> User:
    user.name = name.strip()
    log_activity(
        db,
        user_id=user.id,
        activity_type=ActivityType.PROFILE_UPDATED,
        message=f"Profile updated (name: {user.name})",
        ip=ip,
    )
    db.commit()
    db.refresh(user)
    return user
