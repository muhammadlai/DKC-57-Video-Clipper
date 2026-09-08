"""Health + readiness endpoint."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from aitzaz_api.core.config import get_settings

router = APIRouter(tags=["health"])


def _check_database() -> tuple[str, str | None]:
    from aitzaz_api.db.session import engine

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok", None
    except Exception as exc:  # noqa: BLE001
        return "error", str(exc)[:200]


def _check_redis() -> tuple[str, str | None]:
    settings = get_settings()
    if not settings.redis_url:
        return "not_configured", None
    try:
        import redis  # type: ignore[import-not-found]

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1.5, socket_timeout=1.5)
        client.ping()
        return "ok", None
    except ImportError:
        return "not_installed", "redis package not installed"
    except Exception as exc:  # noqa: BLE001
        return "error", str(exc)[:200]


@router.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    started = time.perf_counter()
    db_status, db_error = _check_database()
    redis_status, redis_error = _check_redis()

    provider_name, provider_demo = settings.llm_provider, settings.llm_provider == "mock"
    if provider_name == "openai" and not settings.openai_api_key:
        provider_name, provider_demo = "mock-demo (fallback)", True
    elif provider_name == "anthropic" and not settings.anthropic_api_key:
        provider_name, provider_demo = "mock-demo (fallback)", True
    elif provider_name == "mock":
        provider_name = "mock-demo"

    overall = "healthy" if db_status == "ok" else "degraded"
    return {
        "status": overall,
        "service": settings.project_name,
        "version": settings.version,
        "environment": settings.environment,
        "time": datetime.now(UTC).isoformat(),
        "uptime_check_ms": int((time.perf_counter() - started) * 1000),
        "components": {
            "database": {"status": db_status, "error": db_error},
            "redis": {"status": redis_status, "error": redis_error},
            "llm": {"provider": provider_name, "demo_mode": provider_demo},
        },
    }
