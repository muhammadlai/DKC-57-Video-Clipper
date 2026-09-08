"""Database engine and session factory."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aitzaz_api.core.config import get_settings


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}


def make_engine(database_url: str):
    return create_engine(database_url, **_engine_kwargs(database_url))


settings = get_settings()
engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — one session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
