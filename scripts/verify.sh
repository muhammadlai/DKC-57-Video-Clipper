#!/usr/bin/env bash
# =============================================================================
# Aitzaz AI — full verification: lint + typecheck + unit tests + migrations
# Run from the repo root:  bash scripts/verify.sh
# The API does NOT need to be running for this script.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-$ROOT/.venv/bin/python}"
FAILURES=0

step() { printf "\n\033[1;35m==> %s\033[0m\n" "$1"; }
pass() { printf "  \033[1;32m✓ %s\033[0m\n" "$1"; }
fail() { printf "  \033[1;31m✗ %s\033[0m\n" "$1"; FAILURES=$((FAILURES+1)); }

step "Backend: ruff lint"
(cd apps/api && "$PY" -m ruff check aitzaz_api tests) && pass "ruff clean" || fail "ruff errors"

step "Backend: pytest suite"
(cd apps/api && "$PY" -m pytest tests/ -q) && pass "unit/API tests" || fail "pytest failed"

step "Frontend: typecheck"
if command -v npm >/dev/null 2>&1; then
  (cd apps/web && npx tsc --noEmit) && pass "tsc clean" || fail "type errors"
  step "Frontend: production build"
  (cd apps/web && npm run build) >/dev/null 2>&1 && pass "next build" || fail "build failed"
  step "Frontend: lint"
  (cd apps/web && npm run lint) && pass "eslint clean" || fail "lint errors"
else
  fail "npm not available — skipped frontend checks"
fi

step "Summary"
if [ "$FAILURES" -eq 0 ]; then
  printf "  \033[1;32mAll checks passed ✅\033[0m\n"
else
  printf "  \033[1;31m%s check group(s) failed ❌\033[0m\n" "$FAILURES"
  exit 1
fi
