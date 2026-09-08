# Architecture

## The core principle

```
ME → AITZAZ AI → TOOLS / SPECIALIST AGENTS → RESULT
```

Aitzaz AI is designed as a **personal agent platform**, not a chatbot. Phase 1
builds the full skeleton so later phases add capabilities without rewrites.

```
┌───────────────────────────────  Browser (ChromeOS)  ───────────────────────────────┐
│  Next.js 14 dashboard (dark/light premium UI)                                      │
│  Overview · Chat · Tasks · Automations · Memory · Tools · Files · Research         │
│  Browser · Agents · Activity · Approvals · Settings                                │
└──────────────────────────────────────┬──────────────────────────────────────────────┘
                     same-origin fetch │ Next.js rewrites → /api/v1/*
┌──────────────────────────────────────▼──────────────────────────────────────────────┐
│  FastAPI (apps/api)                                                                 │
│  auth · chat · agents · tools · memories · tasks · approvals · activity · settings  │
│  session auth (JWT + revocable) · validation · rate limit · audit logging           │
└───────┬──────────────────────────────┬─────────────────────────────┬────────────────┘
        │ SQLAlchemy / Alembic         │ agent runtime               │ optional
┌───────▼──────────────┐   ┌───────────▼─────────────┐   ┌───────────▼───────────┐
│ PostgreSQL 16        │   │ agents/core (Agent,     │   │ Redis (cache/jobs     │
│ 13 tables + indexes  │   │ LLMProvider, Personal   │   │ foundation — graceful │
│ migrations + seeds   │   │ Assistant, Mock/OpenAI/ │   │ fallback if absent)   │
└──────────────────────┘   │ Anthropic providers)    │   └───────────────────────┘
                           │ tools/core (Tool,       │
                           │ ToolRegistry, demo      │
                           │ tools)                  │
                           │ memory/core (types,     │
                           │ MemoryStore protocol)   │
                           └─────────────────────────┘
```

## Monorepo layout & boundaries

| Path | Responsibility | Depends on |
|---|---|---|
| `agents/core` | `Agent` abstraction, `LLMProvider` interface, Mock/OpenAI/Anthropic providers, Personal Assistant loop | `tools/core` |
| `tools/core` | `Tool`, `ToolRegistry`, schema validation, Calculator/CurrentTime/Echo | — (stdlib only) |
| `memory/core` | `MemoryType` taxonomy, `MemoryRecord`, `MemoryStore` protocol, prompt summarizer | — |
| `apps/api` | HTTP layer, persistence, wiring, seeds, migrations | all core packages |
| `apps/web` | Dashboard UI | `packages/*` (types/constants) |
| `packages/types` | API contract types shared with the backend schemas | — |
| `packages/shared` | Brand, nav, status metadata, roadmap | — |

Key rule: **core packages never import the API**. The API adapts them
(e.g. SQLAlchemy implements `MemoryStore`; DB-backed agent tools conform to
`Tool`). This is what keeps Phase 3+ swaps non-breaking.

## Agent runtime (one chat turn)

```
user message
  → PersonalAssistantAgent.run()
      → system prompt (instructions + demo-mode note + tool specs)
      → LLMProvider.complete(messages, tools)
      ├── content → final answer
      └── tool_calls → ToolRegistry.execute (validate → permission → run → time)
              → results appended as tool messages → provider completes
  → messages persisted (user + assistant incl. tool-call metadata)
  → activity logged
```

- The **MockLLMProvider (Demo AI)** pattern-matches math/time/memory/task/
  approval intents and emits the *same tool-call contract* as a real provider —
  so swapping in OpenAI in Phase 2 changes one factory function.
- Tool execution from the agent uses the **same** audited pipeline as the
  Tools page (`tool_service.execute`) — permission checks + activity events.

## Safety / control model (built from Phase 1)

Sensitive external actions follow **REQUEST → HUMAN DECIDES → EXECUTE**:

1. The agent (or you, via the UI) creates an `Approval` with `action_type`,
   human-readable `description` and structured `payload`.
2. Nothing is executed. If the request is linked to a task, the task enters
   `waiting_approval`.
3. You approve or reject on the Approvals page; decisions are recorded
   (`decided_at`, `decision_note`) and audited.
4. Approve → task returns to `pending` (a future connector/executor picks it
   up). Reject → linked task is cancelled.
5. Pending requests auto-expire after 72 h.

Phase 1 has **no connectors** (no email, banking, social…). The architecture
(who requested what, what was approved, what would run) is fully in place.

## Database model (13 tables)

| Table | Purpose | Notable columns / constraints |
|---|---|---|
| `users` | accounts | unique email, bcrypt hash, role, is_active |
| `sessions` | revocable JWT companions | unique jti, expires_at, revoked_at, ip, ua |
| `agents` | agent definitions | unique slug, capabilities/tools JSON, status, is_builtin |
| `agent_configs` | per-agent key/value config | unique (agent_id, key) |
| `conversations` | chat threads | user FK, agent FK, last_message_at |
| `messages` | chat messages | role, content, metadata (provider, tool calls) |
| `tools` | tool registry | unique slug, input/output schema, required_permission, enabled |
| `memories` | long-lived memory | category, importance 1–5 (check), metadata |
| `tasks` | task system | status enum lifecycle, priority, due_at |
| `approvals` | control plane | action_type, payload, status, requested/decided/expires_at |
| `activity_logs` | audit trail | activity_type, message, metadata, ip |
| `settings` | per-user settings JSON | unique user_id |
| `permissions` | permission registry | unique code (role→permissions map in code) |

All tables: UUID PKs, FK cascades where correct, created_at/updated_at,
targeted indexes (see the generated migration
`apps/api/alembic/versions/*_initial_schema_phase_1.py`).

## API surface (prefix `/api/v1`)

```
GET  /health (+ /api/health alias)     POST /auth/register · /auth/login · /auth/logout
GET/PATCH /auth/me                     POST /chat · GET /chat/conversations
GET  /chat/conversations/{id}/messages DELETE /chat/conversations/{id}
GET  /agents · /agents/future · /agents/{slug}
GET  /tools · GET /tools/{slug} · POST /tools/{slug}/execute
GET/POST /memories · GET/PATCH/DELETE /memories/{id}
GET/POST /tasks · GET/PATCH/DELETE /tasks/{id} · GET /tasks/stats
GET/POST /approvals · GET /approvals/{id} · POST /approvals/{id}/decision
GET  /activity (filter by type, paginated)
GET/PATCH /settings (sectioned, validated)
GET  /stats (dashboard) · GET /search?q= (global search)
```

Every error uses one envelope: `{"error": {"code", "message", "details?"}}`.
Validation failures are 422 with field details; auth failures 401; role
gaps 403; duplicates 409; unknown 404. Stack traces never reach clients.

## Security foundation

- bcrypt (12 rounds) password hashing; passwords never logged.
- JWT (HS256) in **httpOnly, SameSite=Lax** cookies; every token is backed by
  a `sessions` row → logout/revocation is real.
- Role → permission map enforced by a `require_permission` dependency.
- In-memory sliding-window rate limiter (Redis-backed swap planned).
- CORS allow-list via env; secrets only via environment; `.env` gitignored.
- Full audit log (including `error` events) written by the service layer.
