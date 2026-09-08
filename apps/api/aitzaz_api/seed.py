"""Idempotent seed script.

Creates: permissions, built-in tools, the Personal Assistant agent and (in
development) the documented demo account. Safe to run repeatedly.

Usage (from apps/api):  python -m app.seed
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from aitzaz_api.core.config import get_settings
from aitzaz_api.db.session import SessionLocal
from aitzaz_api.models.permission import ALL_PERMISSIONS, Permission
from aitzaz_api.services.activity_service import log_activity
from aitzaz_api.services.agent_service import ensure_builtin_agents
from aitzaz_api.services.auth_service import get_user_by_email, register_user
from aitzaz_api.services.tool_service import ensure_builtin_tools


def seed() -> dict:
    settings = get_settings()
    created: dict[str, int] = {}

    db = SessionLocal()
    try:
        # 1. Permissions
        existing_codes = {code for (code,) in db.execute(select(Permission.code)).all()}
        new_permissions = [p for p in ALL_PERMISSIONS if p["code"] not in existing_codes]
        for permission in new_permissions:
            db.add(Permission(code=permission["code"], name=permission["name"]))
        db.commit()
        created["permissions"] = len(new_permissions)

        # 2. Built-in tools (mirrors the code registry)
        ensure_builtin_tools(db)
        created["tools_synced"] = True  # type: ignore[assignment]

        # 3. Built-in agents
        ensure_builtin_agents(db)
        created["agents_synced"] = True  # type: ignore[assignment]

        # 4. Demo account (development only)
        if settings.seed_demo_user and not settings.is_production:
            demo = get_user_by_email(db, settings.demo_user_email)
            if demo is None:
                demo, _token, _exp = register_user(
                    db,
                    name=settings.demo_user_name,
                    email=settings.demo_user_email,
                    password=settings.demo_user_password,
                    ip="seed",
                    user_agent="seed-script",
                    settings=settings,
                )
                log_activity(
                    db,
                    user_id=demo.id,
                    activity_type="seed",
                    message="Demo account created by seed script",
                    ip="seed",
                )
                db.commit()
                created["demo_user"] = 1
            else:
                created["demo_user"] = 0
    finally:
        db.close()

    return created


def main() -> int:
    settings = get_settings()
    print(f"Seeding {settings.project_name} ({settings.environment})…")
    result = seed()
    for key, value in result.items():
        print(f"  {key}: {value}")
    print("Seed complete.")
    if settings.seed_demo_user and not settings.is_production:
        print(
            f"  Demo login → {settings.demo_user_email} / {settings.demo_user_password} "
            "(documented development credentials — do NOT use in production)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
