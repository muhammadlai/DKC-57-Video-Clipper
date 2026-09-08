# Testing

Phase 1 ships three test layers plus a manual plan. Everything below was
executed and passing at time of delivery — re-run any time.

## 1. One command: full verification

```bash
bash scripts/verify.sh
```

Runs backend lint (ruff), the full backend test suite, frontend typecheck
(`tsc --noEmit`), frontend production build (`next build`) and frontend lint
(`next lint`).

## 2. Backend suite (pytest — 83 tests)

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/
```

Covers (isolated SQLite DB per run, real app + real auth):

- **health**: `/api/health`, `/api/v1/health`, OpenAPI completeness
- **auth**: register, duplicate email (409), weak password (422), login,
  wrong password (401), cookie flags (httpOnly), `/auth/me` via token and via
  cookie, logout revocation, garbage/expired tokens, profile update
- **chat**: Demo AI greeting, calculator tool call (125 × 48 = 6000), time
  tool, agent-created tasks, agent-created approval requests, agent-created
  memories, conversation history/list/clear, auth required, empty message
- **tools**: list, execute calculator (incl. `×` symbol), code-injection
  rejection, schema violations (422), unknown tool (404), echo, auth required
- **tasks**: CRUD, defaults, priority/status validation, legal + illegal
  status transitions (409), user isolation, stats
- **memories**: CRUD, category normalization, importance bounds, search
- **approvals**: create, invalid action type, approve, reject with note,
  double-decision (409), task linking (`waiting_approval` → pending/cancelled),
  status filters
- **activity/settings/agents**: audit events for login/logout/task/tool/
  settings, filters, settings round-trip + section validation, agent listing,
  future agents, dashboard stats, global search
- **units**: bcrypt roundtrip + salting, JWT roundtrip/expiry/bad secret,
  calculator AST safety (no `eval`), registry permission/validation paths,
  mock-LLM intents + demo labelling, provider factory fallback

## 3. End-to-end journey (real HTTP + real PostgreSQL)

Start the stack, then:

```bash
python scripts/e2e_flow.py          # --fresh for a brand-new account
```

20 assertions over the whole spec §19 journey: health → login → dashboard →
chat (Demo AI) → calculator via chat → create task → create memory → execute
calculator tool → create approval → approve → activity contains every event →
logout (session revoked) → login again → task/memory/approval persisted.

## 4. Frontend verification

```bash
cd apps/web
npx tsc --noEmit     # types
npm run build        # production build — also prerenders every page (catches SSR bugs)
npm run lint         # eslint (next/core-web-vitals)
```

Every dashboard route was additionally smoke-tested over HTTP (200 with a
session cookie, 307 → `/login` without one).

**Browser-level E2E (optional, on your machine):** a Playwright spec covering
register → chat → task → memory → tool → approval → activity → logout is
provided at `apps/web/e2e/phase1.spec.ts`. This sandbox could not download
Chromium (blocked egress), so run it locally:

```bash
cd apps/web
npm i -D playwright && npx playwright install chromium
BACKEND_ORIGIN=http://127.0.0.1:8000 npx playwright test --config e2e/playwright.config.ts
```

## 5. Migrations

```bash
cd apps/api
export AITZAZ_DATABASE_URL='postgresql+psycopg2://aitzaz:aitzaz@localhost:5432/aitzaz'
alembic upgrade head      # create all 13 tables (+ alembic_version)
alembic downgrade base    # remove them
alembic upgrade head      # re-create — verified round-trip
```

## 6. Manual test plan (10 minutes)

Sign in at http://localhost:3000 (or register a new account):

1. **Chat** — send `Hello Aitzaz` → Demo AI introduces itself (badge shown)
2. **Math** — send `Calculate 125 × 48` → tool chip `calculator ✓` + “6,000”
3. **Time** — send `What time is it?` → current_time tool answer
4. **Tasks** — send `Remind me to call the bank tomorrow` → Tasks page shows it
5. **Memory** — send `Remember that I prefer concise answers` → Memory page shows it
6. **Tools** — Tools page → Calculator → Execute → JSON result panel
7. **Approvals** — send `Send an email to John` → pending request appears;
   Approve it → status flips to approved, note recorded
8. **Activity** — login/message/task/tool/approval events all listed
9. **Settings** — change display name; toggle theme; reload → persisted
10. **Persistence** — logout, login again → task, memory, approval, settings
    all still there
