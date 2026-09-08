# Infrastructure

Phase 1 keeps infrastructure deliberately simple.

## Provided today

- `docker-compose.yml` (repo root): web + api + postgres 16 + redis 7 with
  healthchecks and volume persistence.
- `apps/api/Dockerfile` — python:3.12-slim, installs the three core packages
  plus the API, runs migrations + seed on start.
- `apps/web/Dockerfile` — node:20 multi-stage build → Next.js standalone.

## Phase 12 (production hardening) will add

- Managed Postgres + automated backups/restore drills
- Reverse proxy (TLS, HSTS), image scanning, CI/CD pipelines
- Redis-backed rate limiting and job queue workers
- Secrets management, monitoring/alerting, error tracking
- Multi-environment deploy configs (staging/production)

Until then: single-host `docker compose` is the intended deployment shape,
with a strong `AITZAZ_SECRET_KEY` and `AITZAZ_ENVIRONMENT=production`
(which enforces secret strength and disables demo seeding).
