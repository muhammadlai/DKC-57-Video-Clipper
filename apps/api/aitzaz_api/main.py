"""FastAPI application factory for Aitzaz AI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from aitzaz_api.api.router import api_router
from aitzaz_api.api.v1.health import router as health_router
from aitzaz_api.core.config import get_settings
from aitzaz_api.core.errors import register_exception_handlers
from aitzaz_api.core.logging_config import configure_logging
from aitzaz_api.core.rate_limit import RateLimitMiddleware

logger = logging.getLogger("aitzaz.main")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-ID and log method/path/status/duration."""

    async def dispatch(self, request: Request, call_next):
        import time
        import uuid

        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%s ms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


def _startup_tasks() -> None:
    """Idempotent bootstrap: schema (dev), built-in tools & agents."""
    settings = get_settings()
    if settings.auto_create_tables:
        import aitzaz_api.models  # noqa: F401 — register metadata
        from aitzaz_api.db.base import Base
        from aitzaz_api.db.session import engine

        Base.metadata.create_all(bind=engine)

    from aitzaz_api.db.session import SessionLocal
    from aitzaz_api.services.agent_service import ensure_builtin_agents
    from aitzaz_api.services.tool_service import ensure_builtin_tools

    db = SessionLocal()
    try:
        ensure_builtin_tools(db)
        ensure_builtin_agents(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.validate_secrets()
    configure_logging(settings.log_level)
    logger.info("Starting %s v%s (%s)", settings.project_name, settings.version, settings.environment)
    _startup_tasks()
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.project_name,
        description=settings.project_description
        + ". Personal AI agent with tools, memory, tasks, approvals and a full audit trail.",
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware (order matters: last added runs first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(
        RateLimitMiddleware,
        enabled=settings.rate_limit_enabled,
        per_minute=settings.rate_limit_per_minute,
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "service": settings.project_name,
            "version": settings.version,
            "docs": "/docs",
            "api": settings.api_v1_prefix,
            "health": "/api/health",
        }

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    # Convenient alias so health is also available at /api/health
    app.include_router(health_router, prefix="/api")
    return app


app = create_app()
