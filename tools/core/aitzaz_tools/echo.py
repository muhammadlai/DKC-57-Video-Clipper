"""Echo/test tool — verifies that tool execution works end to end."""

from __future__ import annotations

import time
from typing import Any

from aitzaz_tools.base import Tool, ToolContext


class EchoTool(Tool):
    slug = "echo"
    name = "Echo (Test)"
    description = (
        "Test tool that echoes a message back. Use it to verify that the "
        "tool execution pipeline works."
    )
    category = "testing"
    input_schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "minLength": 1,
                "maxLength": 2000,
                "description": "Text to echo back",
            },
            "delay_ms": {
                "type": "integer",
                "minimum": 0,
                "maximum": 2000,
                "description": "Optional simulated latency in milliseconds",
                "default": 0,
            },
        },
        "required": ["message"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "echoed_at": {"type": "string"},
        },
    }

    def execute(self, input_data: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        delay = int(input_data.get("delay_ms") or 0)
        if delay:
            time.sleep(min(delay, 2000) / 1000)
        return {
            "message": input_data["message"],
            "echoed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "actor": ctx.actor,
        }
