# Tests

Phase 1 test suites live next to the code they verify:

| Suite | Location | Command |
|---|---|---|
| Backend unit + API tests (83) | [`apps/api/tests/`](../apps/api/tests/) | `cd apps/api && ../../.venv/bin/python -m pytest tests/` |
| End-to-end HTTP journey (20 checks) | [`scripts/e2e_flow.py`](../scripts/e2e_flow.py) | run the stack, then `python scripts/e2e_flow.py` |
| Frontend typecheck/build/lint | [`apps/web/`](../apps/web/) | `bash scripts/verify.sh` |
| Browser E2E (Playwright) | [`apps/web/e2e/`](../apps/web/e2e/) | see docs/TESTING.md (needs Chromium download) |

Everything is orchestrated by `bash scripts/verify.sh`.
See [docs/TESTING.md](../docs/TESTING.md) for the full guide.
