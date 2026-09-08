"""Current-time demo tool — returns configured server/application time."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

from aitzaz_tools.base import Tool, ToolContext, ToolInputError

try:  # tzdata package provides the IANA database on slim images
    import tzdata  # noqa: F401

    _HAS_TZDATA = True
except ImportError:  # pragma: no cover
    _HAS_TZDATA = False


class CurrentTimeTool(Tool):
    slug = "current_time"
    name = "Current Time"
    description = (
        "Returns the current server time (ISO-8601, human-friendly form, "
        "Unix timestamp and day of week). Use whenever the user asks about "
        "the current date or time."
    )
    category = "utility"
    input_schema = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "maxLength": 64,
                "description": "Optional IANA timezone, e.g. 'Asia/Karachi'",
            }
        },
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "iso": {"type": "string"},
            "friendly": {"type": "string"},
            "timezone": {"type": "string"},
            "unix": {"type": "number"},
            "day_of_week": {"type": "string"},
        },
    }

    def execute(self, input_data: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        tz_name = input_data.get("timezone") or ctx.config.get("default_timezone", "UTC")
        try:
            tz = ZoneInfo(tz_name)
        except Exception as exc:  # noqa: BLE001
            raise ToolInputError(
                f"Unknown timezone '{tz_name}'. Use an IANA name like 'UTC' or 'Asia/Karachi'."
            ) from exc

        now = datetime.now(tz)
        return {
            "iso": now.isoformat(),
            "friendly": now.strftime("%A, %d %B %Y at %H:%M (%Z)"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": str(tz),
            "utc_offset": now.strftime("%z"),
            "unix": int(now.timestamp()),
            "day_of_week": now.strftime("%A"),
            "utc_iso": datetime.now(dt_timezone.utc).isoformat(),
        }
