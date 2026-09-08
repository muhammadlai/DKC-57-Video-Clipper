# Database

Migrations live with the backend that owns the models:

- **Schema/migrations:** [`apps/api/alembic/`](../apps/api/alembic/) (Alembic,
  generated from the SQLAlchemy models in `apps/api/aitzaz_api/models/`)
- **Seed script (idempotent):** `apps/api/aitzaz_api/seed.py`
  → `cd apps/api && ../../.venv/bin/python -m aitzaz_api.seed`

## Apply migrations

```bash
cd apps/api
alembic upgrade head      # needs AITZAZ_DATABASE_URL (from .env / environment)
```

## Current schema (Phase 1)

`users`, `sessions`, `agents`, `agent_configs`, `conversations`, `messages`,
`tools`, `memories`, `tasks`, `approvals`, `activity_logs`, `settings`,
`permissions` (+ `alembic_version`).

Details and constraints: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
