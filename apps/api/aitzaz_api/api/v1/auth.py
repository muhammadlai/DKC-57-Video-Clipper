"""Auth endpoints: register, login, logout, me, profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from aitzaz_api.core.config import Settings, get_settings
from aitzaz_api.core.deps import (
    CurrentUser,
    DbSession,
    get_client_ip,
    get_token,
    get_user_agent,
)
from aitzaz_api.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    UserResponse,
)
from aitzaz_api.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, settings: Settings, expires_at) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(
    payload: RegisterRequest,
    response: Response,
    db: DbSession,
    ip: str | None = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
) -> AuthResponse:
    settings = get_settings()
    user, token, expires_at = auth_service.register_user(
        db,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        ip=ip,
        user_agent=user_agent,
        settings=settings,
    )
    _set_session_cookie(response, token, settings, expires_at)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
        expires_at=expires_at,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
    ip: str | None = Depends(get_client_ip),
    user_agent: str | None = Depends(get_user_agent),
) -> AuthResponse:
    settings = get_settings()
    user, token, expires_at = auth_service.authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
        ip=ip,
        user_agent=user_agent,
        settings=settings,
    )
    _set_session_cookie(response, token, settings, expires_at)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
        expires_at=expires_at,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    db: DbSession,
    user: CurrentUser,
    token: str | None = Depends(get_token),
    ip: str | None = Depends(get_client_ip),
) -> MessageResponse:
    settings = get_settings()
    if token:
        from aitzaz_api.core.security import decode_token

        try:
            payload = decode_token(token, secret_key=settings.secret_key, algorithm=settings.jwt_algorithm)
            auth_service.logout_user(db, user=user, jti=payload["jti"], ip=ip)
        except Exception:  # noqa: BLE001 — logging out with an expired token still clears the cookie
            db.rollback()
    response.delete_cookie(key=settings.cookie_name, path="/")
    return MessageResponse(message="Signed out")


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: ProfileUpdateRequest,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> UserResponse:
    updated = auth_service.update_profile(db, user=user, name=payload.name, ip=ip)
    return UserResponse.model_validate(updated)
