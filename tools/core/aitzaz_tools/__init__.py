"""Aitzaz AI — core tool abstraction and Phase 1 demo tools."""

from aitzaz_tools.base import (
    Tool,
    ToolContext,
    ToolDisabledError,
    ToolError,
    ToolInputError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolRegistry,
    ToolResult,
)
from aitzaz_tools.calculator import CalculatorTool
from aitzaz_tools.current_time import CurrentTimeTool
from aitzaz_tools.echo import EchoTool

__all__ = [
    "Tool",
    "ToolContext",
    "ToolError",
    "ToolResult",
    "ToolRegistry",
    "ToolNotFoundError",
    "ToolDisabledError",
    "ToolInputError",
    "ToolPermissionError",
    "CalculatorTool",
    "CurrentTimeTool",
    "EchoTool",
]


def build_demo_tools() -> list[Tool]:
    """Return the safe Phase 1 demo tools (calculator, current time, echo)."""
    return [CalculatorTool(), CurrentTimeTool(), EchoTool()]
