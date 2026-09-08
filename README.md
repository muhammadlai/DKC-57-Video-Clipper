# Aitzaz AI — Personal AI Agent

> **ME → AITZAZ AI → TOOLS / SPECIALIST AGENTS → RESULT**

Aitzaz AI is a personal AI agent designed to become your central digital
assistant: it chats, uses tools, remembers what matters, manages tasks, and —
critically — **asks for your approval before doing anything sensitive**.

**Current status: PHASE 1 — Foundation complete and fully tested.**
Authentication, dashboard, chat (Demo AI), tools, memory, tasks, approvals,
activity log, settings — all real, all persisted, all tested.

---

## Highlights

- 🧠 **Agent architecture** — reusable `Agent` abstraction + built-in
  **Personal Assistant** agent, ready for specialist sub-agents later.
- 🔌 **LLM provider abstraction** — `LLMProvider` interface with a clearly
  labelled **Demo AI** (mock) and OpenAI/Anthropic implementations behind env
  configuration. Never hard-coded to one vendor.
- 🧰 **Tool system** — validated, permission-checked, audited tools
  (Calculator, Current Time, Echo + agent tools for tasks/memory/approvals).
- 🗃️ **Memory foundation** — typed, categorized memories with a swappable
  store (vector/RAG plugs in at Phase 3 without rewrites).
- ✅ **Task system** — full status lifecycle incl. `waiting_approval`.
- 🔐 **Approval workflow** — `REQUEST → HUMAN DECIDES → EXECUTE`. The agent
  can prepare emails/purchases/deletions but never acts without you.
- 📜 **Complete audit trail** — every login, message, tool run and decision is
  logged and visible in the Activity page.
- 🛡️ **Security foundation** — bcrypt, revocable JWT sessions in httpOnly
  cookies, rate limiting, strict validation, consistent error envelope.
- 💻 **Chromebook-first UI** — premium dark/light dashboard that runs entirely
  in Chrome. No local GPU, no installs, no desktop apps.

## Quick start (Docker — recommended)

```bash
docker compose up --build
```

Open **http://localhost:3000** and sign in:

| | |
|---|---|
| Email | `demo@aitzaz.ai` |
| Password | `demo-user-2026` |

(documented development credentials created by the seed script — change or
disable for any real deployment). API docs: http://localhost:8000/docs ·
Health: http://localhost:8000/api/health

## Quick start (no Docker)

```bash
bash scripts/install.sh          # venv + deps + .env with a generated secret
docker compose up db redis       # or use SQLite: set AITZAZ_DATABASE_URL=sqlite:///./aitzaz-dev.db

cd apps/api && ../../.venv/bin/alembic upgrade head
cd apps/api && ../../.venv/bin/python -m aitzaz_api.seed
cd apps/api && ../../.venv/bin/uvicorn aitzaz_api.main:app --reload --port 8000   # terminal 1
cd apps/web && npm run dev                                                        # terminal 2
```

Open http://localhost:3000 — full details in **docs/SETUP.md**.

## What works in Phase 1 (Demo mode)

1. Register / login / logout with real session security
2. Chat with the **Demo AI** (rule-based mock — labelled as demo everywhere)
3. “Calculate 125 × 48” → Calculator tool runs and answers
4. “What time is it?” → Current Time tool
5. “Remind me to call the bank tomorrow” → a real task is created
6. “Remember that I prefer concise answers” → a real memory is stored
7. “Send an email to John” → an **approval request** is created instead
8. Approve / reject requests on the Approvals page
9. Everything recorded on the Activity page — log in again and it persists

> The Demo AI is **not** a real LLM — it's a deterministic mock so the whole
> pipeline works without API keys. Phase 2 connects real providers through the
> existing `LLMProvider` interface.

## Repository layout

```
aitzaz-ai/
├── apps/
│   ├── web/            # Next.js 14 + TypeScript + Tailwind dashboard
│   └── api/            # FastAPI + SQLAlchemy + Alembic backend
├── packages/
│   ├── shared/         # brand/nav/status constants
│   └── types/          # shared API contract types
├── agents/core/        # Agent abstraction + LLM providers (Python)
├── tools/core/         # Tool abstraction + demo tools (Python)
├── memory/core/        # Memory abstraction (Python)
├── database/           # notes; migrations live in apps/api/alembic
├── infrastructure/     # deployment notes
├── scripts/            # install.sh · verify.sh · e2e_flow.py
├── tests/              # (workspace-level test notes; suites live in apps)
├── docs/               # ARCHITECTURE · SETUP · TESTING · ROADMAP
├── docker-compose.yml  # web + api + postgres + redis
├── .env.example
└── README.md
```

## Verify everything yourself

```bash
bash scripts/verify.sh            # lint + typecheck + 83 backend tests + build
python scripts/e2e_flow.py        # 20-step end-to-end journey (needs API running)
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design, data model, control plane
- [docs/SETUP.md](docs/SETUP.md) — environment, database, running, troubleshooting
- [docs/TESTING.md](docs/TESTING.md) — test suites, E2E, manual test plan
- [docs/ROADMAP.md](docs/ROADMAP.md) — Phases 2–12

## License

MIT — see [LICENSE](LICENSE).
