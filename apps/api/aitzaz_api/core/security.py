"""Password hashing (bcrypt) and JWT creation/verification.

Tokens are opaque to the browser: they live in an httpOnly cookie and every
token is backed by a row in the ``sessions`` table so logout/revocation is
real, not cosmetic.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt


class TokenError(Exception):
    """Raised when a token is invalid, expired or malformed."""


def hash_password(password: str, *, rounds: int = 12) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    password_bytes = password.encode("utf-8")[:72]  # bcrypt 72-byte limit
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *,
    subject: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_minutes: int = 60 * 24 * 7,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Create a signed JWT. Returns ``(token, jti, expires_at)``."""
    jti = uuid.uuid4().hex
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, secret_key, algorithm=algorithm)
    return token, jti, expires_at


def decode_token(token: str, *, secret_key: str, algorithm: str = "HS256") -> dict[str, Any]:
    """Decode and validate a JWT, raising :class:`TokenError` on any problem."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise TokenError("Token is invalid") from exc

    if payload.get("type") != "access" or not payload.get("sub") or not payload.get("jti"):
        raise TokenError("Token is invalid")
    return payload
