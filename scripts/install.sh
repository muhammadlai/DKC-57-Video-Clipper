#!/usr/bin/env bash
# =============================================================================
# Aitzaz AI — one-command local development setup (no Docker required)
# Creates a venv, installs backend + frontend dependencies, prepares .env.
# Docker users: just run `docker compose up --build` instead.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Setting up Aitzaz AI (repo root: $ROOT)"

# 1. Python venv
if [ ! -d ".venv" ]; then
  echo "==> Creating Python virtualenv (.venv)"
  python3 -m venv .venv
fi
PY="$ROOT/.venv/bin/python"
PIP="$ROOT/.venv/bin/pip"

echo "==> Installing core agent/tool/memory packages (editable)"
"$PIP" install --quiet -e "$ROOT/agents/core" -e "$ROOT/tools/core" -e "$ROOT/memory/core"

echo "==> Installing API dependencies"
"$PIP" install --quiet -r "$ROOT/apps/api/requirements.txt" -r "$ROOT/apps/api/requirements-dev.txt"

# 2. Environment file
if [ ! -f ".env" ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
  SECRET=$("$PY" -c "import secrets; print(secrets.token_urlsafe(48))")
  sed -i.bak "s|^AITZAZ_SECRET_KEY=.*|AITZAZ_SECRET_KEY=$SECRET|" .env && rm -f .env.bak
  echo "    (generated a random AITZAZ_SECRET_KEY for you)"
fi

# 3. Frontend deps
if command -v npm >/dev/null 2>&1; then
  echo "==> Installing frontend dependencies"
  (cd "$ROOT/apps/web" && npm install --no-audit --no-fund)
else
  echo "!! npm not found — install Node.js 18+ to run the dashboard"
fi

# 4. Database hint
echo
echo "Setup complete. Next steps:"
echo "  • Easiest DB:   docker compose up db redis        (PostgreSQL + Redis)"
echo "                  then set AITZAZ_DATABASE_URL in .env (already default)"
echo "  • Or SQLite:    set AITZAZ_DATABASE_URL=sqlite:///./aitzaz-dev.db in .env"
echo
echo "  Run backend:    cd apps/api && ../../.venv/bin/alembic upgrade head"
echo "                  cd apps/api && ../../.venv/bin/python -m aitzaz_api.seed"
echo "                  cd apps/api && ../../.venv/bin/uvicorn aitzaz_api.main:app --reload --port 8000"
echo "  Run frontend:   cd apps/web && npm run dev"
echo "  Open:           http://localhost:3000"
