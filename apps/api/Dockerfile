# Aitzaz AI — FastAPI backend
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 (wheel exists, but libpq runtime is tiny and safe)
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# --- Core python packages (monorepo layout) ---
COPY agents/core /deps/agents/core
COPY tools/core /deps/tools/core
COPY memory/core /deps/memory/core
RUN pip install --no-cache-dir \
    /deps/agents/core /deps/tools/core /deps/memory/core

# --- API ---
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY apps/api /app/apps/api

WORKDIR /app/apps/api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# Run migrations, seed built-ins, then start
CMD ["sh", "-c", "alembic upgrade head && python -m aitzaz_api.seed && uvicorn aitzaz_api.main:app --host 0.0.0.0 --port 8000"]
