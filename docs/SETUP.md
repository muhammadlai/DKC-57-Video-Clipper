# Setup Guide

## Requirements

| | |
|---|---|
| OS / device | Any (built for ChromeOS + Chrome browser) |
| Docker | Docker + Docker Compose **(easiest path)** |
| or local | Python 3.11+, Node.js 18+, npm |
| Database | PostgreSQL 16 (docker) **or** SQLite (zero-setup dev) |

---

## Option A — Docker (recommended)

```bash
cp .env.example .env          # optional: set a real AITZAZ_SECRET_KEY
docker compose up --build
```

- Dashboard: **http://localhost:3000**
- API: http://localhost:8000 · OpenAPI docs at `/docs` · health at `/api/health`

The API container runs migrations (`alembic upgrade head`) and the idempotent
seed (built-in tools/agents + the demo account) on every start.

Sign in with the documented development credentials:

```
email:    demo@aitzaz.ai
password: demo-user-2026
```

---

## Option B — Local, without Docker

```bash
bash scripts/install.sh
```

This creates `.venv`, installs all Python/Node dependencies and writes a
`.env` with a generated secret.

### 1. Choose a database

**PostgreSQL** (matches production; docker makes it easy):

```bash
docker compose up -d db
# .env already contains: AITZAZ_DATABASE_URL=postgresql+psycopg2://aitzaz:aitzaz@localhost:5432/aitzaz
```

**SQLite** (zero setup, fine for a quick look): set in `.env`:

```
AITZAZ_DATABASE_URL=sqlite:///./aitzaz-dev.db
AITZAZ_AUTO_CREATE_TABLES=true
```

### 2. Migrate + seed + run

```bash
cd apps/api
../../.venv/bin/alembic upgrade head            # create schema
../../.venv/bin/python -m aitzaz_api.seed       # idempotent: permissions, tools, agent, demo user
../../.venv/bin/uvicorn aitzaz_api.main:app --reload --port 8000
```

```bash
cd apps/web
npm run dev       # http://localhost:3000  (proxies /api/v1 → :8000)
```

---

## Environment variables (all prefixed `AITZAZ_`)

See [.env.example](../.env.example) for the full documented list. The ones
that matter most:

| Variable | Default | Notes |
|---|---|---|
| `AITZAZ_ENVIRONMENT` | development | `production` enforces strong secrets |
| `AITZAZ_SECRET_KEY` | dev value | **must** be a strong random value in production |
| `AITZAZ_DATABASE_URL` | local postgres | SQLite supported for dev/tests |
| `AITZAZ_LLM_PROVIDER` | mock | `mock` \| `openai` \| `anthropic` |
| `AITZAZ_OPENAI_API_KEY` / `AITZAZ_ANTHROPIC_API_KEY` | empty | required for real providers |
| `AITZAZ_CORS_ORIGINS` | localhost:3000 | JSON list of allowed origins |
| `BACKEND_ORIGIN` | http://127.0.0.1:8000 | frontend → backend proxy target |

**Never put API keys in frontend code.** Keys live only in backend
environment. `.env` is gitignored; commit only `.env.example`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Cannot reach the Aitzaz AI server` banner | API isn't running on `:8000` — start it, check `curl localhost:8000/api/health` |
| Login loops back to `/login` | Cookies blocked — use `http://localhost:3000` (not a different host) |
| `relation "users" does not exist` | Run `alembic upgrade head` (or set `AITZAZ_AUTO_CREATE_TABLES=true` in dev) |
| Demo AI replies feel canned | Expected — it's the rule-based mock. Phase 2 connects a real LLM. |
| Port already in use | Change ports in `docker-compose.yml` or pass `--port` flags |
