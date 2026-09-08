# Roadmap

Phase 1 is complete: foundation, architecture, authentication, dashboard,
agent/tool/memory/task/approval abstractions, testing and docs. Each later
phase extends the existing abstractions — no rewrites.

| Phase | Focus | What plugs in where |
|---|---|---|
| ✅ **1** | **Foundation, auth, dashboard, agent/tool/memory/task/approval architecture, testing** | shipped |
| 2 | Real LLM providers + advanced agent configuration | implement `LLMProvider` hardening; factory already supports openai/anthropic; settings UI section reserved |
| 3 | Long-term semantic memory + RAG | implement `MemoryStore` protocol with a vector DB; `summarize_for_prompt` already exists |
| 4 | Web research agent | new `AgentDefinition` + research tools in `tools/core`; register like the demo tools |
| 5 | Browser automation agent | same — tools with `execution="browser"`; approvals gate consequential actions |
| 6 | File/document intelligence | file tools + Files page becomes real |
| 7 | Voice assistant | streaming transport over the same agent loop |
| 8 | Email/calendar integrations | connectors consume **approved** `Approval` rows (payload schema already stored) |
| 9 | Automation/scheduling engine | task lifecycle + `due_at` already modeled; add worker + triggers |
| 10 | Specialist sub-agents + orchestration | `Agent` registry exists; `agent_configs` table ready |
| 11 | Mobile/PWA experience | dashboard is responsive today; add manifest/service worker |
| 12 | Production hardening | MFA, session UI, Redis rate limiter swap, deployments, monitoring |

## Principles carried forward

1. **Approval-gated by default** — any consequential action waits for a human.
2. **Provider-agnostic** — nothing is hard-coded to one LLM/vendor.
3. **Audited** — every meaningful action lands in `activity_logs`.
4. **Chromebook-first** — heavy work on the backend; browser is the only
   client requirement.
5. **Honest UI** — no fake buttons; unshipped features say "coming in a later
   phase".
