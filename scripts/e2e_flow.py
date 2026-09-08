"""End-to-end test: full Phase 1 user journey over real HTTP + real PostgreSQL.

REGISTER/LOGIN → DASHBOARD → SEND MESSAGE → DEMO AI RESPONDS → CREATE TASK
→ CREATE MEMORY → EXECUTE CALCULATOR TOOL → REQUEST APPROVAL → APPROVE
→ ACTIVITY LOG UPDATED → LOGOUT → LOGIN AGAIN → DATA PERSISTS

Usage (with the API running on :8000):
    python scripts/e2e_flow.py            # uses the demo account
    python scripts/e2e_flow.py --fresh    # creates a unique new account
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:8000"

PASSED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        raise SystemExit(f"E2E FAILED at: {label} {detail}")
    PASSED += 1


def request(method: str, path: str, body: dict | None = None, token: str | None = None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read().decode()
            return response.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, {"raw": payload}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true", help="use a brand-new account")
    args = parser.parse_args()

    print(f"Aitzaz AI — Phase 1 E2E flow against {BASE}\n")

    started = time.time()

    # 0. Health
    status, health = request("GET", "/api/health")
    check("health endpoint is healthy", status == 200 and health["status"] == "healthy")
    check("running in Demo AI mode", health["components"]["llm"]["demo_mode"] is True)

    # 1. REGISTER / LOGIN
    if args.fresh:
        email = f"e2e-{uuid.uuid4().hex[:8]}@aitzaz.test"
        password = "e2e-password-123"
        status, body = request(
            "POST", "/api/v1/auth/register",
            {"name": "E2E Tester", "email": email, "password": password},
        )
        check("register new account", status == 201 and body.get("user", {}).get("email") == email)
    else:
        email, password = "demo@aitzaz.ai", "demo-user-2026"
        status, body = request("POST", "/api/v1/auth/login", {"email": email, "password": password})
        check("login with documented demo credentials", status == 200 and "access_token" in body)
    token = body["access_token"]
    user = body["user"]
    check("current user resolves (auth/me)", request("GET", "/api/v1/auth/me", token=token)[0] == 200)

    # 2. DASHBOARD data
    status, stats = request("GET", "/api/v1/stats", token=token)
    check("dashboard stats endpoint", status == 200 and "tasks" in stats and "demo_mode" in stats)

    # 3. SEND MESSAGE → DEMO AI RESPONDS
    status, chat = request("POST", "/api/v1/chat", {"message": "Hello Aitzaz"}, token=token)
    conversation_id = str(chat.get("conversation_id", ""))
    check(
        "chat: Demo AI responds",
        status == 200 and chat.get("demo_mode") is True and chat["assistant_message"]["content"],
        f"status={status}",
    )

    # 4. Agent answers math via the calculator tool
    status, chat2 = request(
        "POST", "/api/v1/chat",
        {"message": "Calculate 125 × 48", "conversation_id": conversation_id},
        token=token,
    )
    slugs = [c["slug"] for c in chat2.get("tool_calls", [])]
    check("chat: calculator tool executed", "calculator" in slugs and status == 200)
    calc = next((c for c in chat2.get("tool_calls", []) if c["slug"] == "calculator"), {})
    check("chat: calculator result is 6000", calc.get("ok") is True and calc.get("result", {}).get("result") == 6000)

    # 5. CREATE TASK (UI path)
    status, task = request(
        "POST", "/api/v1/tasks",
        {"title": "E2E: prepare the demo report", "priority": "high"},
        token=token,
    )
    check("create task", status == 201 and task.get("status") == "pending")

    # 6. CREATE MEMORY
    status, memory = request(
        "POST", "/api/v1/memories",
        {"content": "E2E memory: I prefer concise summaries", "category": "preference", "importance": 4},
        token=token,
    )
    check("create memory", status == 201 and memory.get("category") == "preference")

    # 7. EXECUTE CALCULATOR TOOL (Tools page path)
    status, tool_run = request(
        "POST", "/api/v1/tools/calculator/execute",
        {"input": {"expression": "500 × 25"}},
        token=token,
    )
    check(
        "execute calculator tool",
        status == 200 and tool_run.get("ok") and tool_run.get("result", {}).get("result") == 12500,
    )

    # 8. REQUEST APPROVAL
    status, approval = request(
        "POST", "/api/v1/approvals",
        {
            "action_type": "send_email",
            "description": "E2E: send the report to John",
            "payload": {"to": "john@example.com", "subject": "Report"},
        },
        token=token,
    )
    check("create approval request", status == 201 and approval.get("status") == "pending")
    approval_id = approval["id"]

    # 9. APPROVE
    status, decided = request(
        "POST", f"/api/v1/approvals/{approval_id}/decision", {"decision": "approved"}, token=token
    )
    check("approve the request", status == 200 and decided.get("status") == "approved")

    # 10. ACTIVITY LOG UPDATED
    status, activity = request("GET", "/api/v1/activity", token=token)
    types = {item["activity_type"] for item in activity.get("items", [])}
    expected_types = {
        "login", "ai_message", "task_created", "memory_created",
        "tool_executed", "approval_requested", "approval_approved",
    }
    missing = expected_types - types
    check("activity log captured the whole journey", status == 200 and not missing, f"missing={missing}")

    # 11. LOGOUT
    status, _ = request("POST", "/api/v1/auth/logout", token=token)
    check("logout", status == 200)
    status, _me = request("GET", "/api/v1/auth/me", token=token)
    check("session revoked after logout (401)", status == 401)

    # 12. LOGIN AGAIN — data persists
    if args.fresh:
        status, body = request("POST", "/api/v1/auth/login", {"email": email, "password": password})
    else:
        status, body = request("POST", "/api/v1/auth/login", {"email": email, "password": password})
    check("login again", status == 200)
    token2 = body["access_token"]

    status, tasks = request("GET", "/api/v1/tasks", token=token2)
    check(
        "task persisted across sessions",
        any(t["title"].startswith("E2E:") for t in tasks.get("items", [])),
    )
    status, memories = request("GET", "/api/v1/memories", token=token2)
    check(
        "memory persisted across sessions",
        any(m["content"].startswith("E2E memory:") for m in memories.get("items", [])),
    )
    status, approvals = request("GET", "/api/v1/approvals", token=token2)
    check(
        "approval decision persisted",
        any(a["id"] == approval_id and a["status"] == "approved" for a in approvals.get("items", [])),
    )

    print(f"\nALL {PASSED} E2E CHECKS PASSED in {time.time() - started:.1f}s ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
