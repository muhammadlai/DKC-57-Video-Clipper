"""Auth schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from aitzaz_api.schemas.common import ORMModel

# Strict-but-practical email validation (no live DNS checks — a personal
# agent must accept addresses on private/internal domains too).
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def _validate_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value) or len(value) > 254:
        raise ValueError("Enter a valid email address")
    return value


EmailStrV = Annotated[str, AfterValidator(_validate_email)]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStrV
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStrV
    password: str = Field(min_length=1, max_length=128)


class UserResponse(ORMModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class AuthResponse(BaseModel):
    """Returned on register/login. The session cookie is set as well."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class ProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class MessageResponse(BaseModel):
    message: str
