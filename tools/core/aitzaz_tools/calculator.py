"""Calculator tool — safe arithmetic evaluation (no eval of arbitrary code)."""

from __future__ import annotations

import ast
import operator
from typing import Any

from aitzaz_tools.base import Tool, ToolContext, ToolInputError

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Guards against absurd computations (DoS via huge exponents etc.).
_MAX_ABS_BASE = 1e100
_MAX_EXPONENT = 1000

_NORMALIZATIONS = {
    "×": "*",
    "✕": "*",
    "x": "*",
    "÷": "/",
    "−": "-",
    ",": "",
}


class CalculatorTool(Tool):
    slug = "calculator"
    name = "Calculator"
    description = (
        "Safely evaluates an arithmetic expression "
        "(+ - * / // % ** and parentheses). Use for any math question."
    )
    category = "math"
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
                "description": "Arithmetic expression, e.g. '125 * 48'",
            }
        },
        "required": ["expression"],
        "additionalProperties": False,
    }
    output_schema = {
        "type": "object",
        "properties": {
            "expression": {"type": "string"},
            "result": {"type": "number"},
            "formatted": {"type": "string"},
        },
    }

    def execute(self, input_data: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        raw = input_data["expression"].strip()
        normalized = raw
        for needle, replacement in _NORMALIZATIONS.items():
            normalized = normalized.replace(needle, replacement)

        try:
            tree = ast.parse(normalized, mode="eval")
            value = self._eval_node(tree.body)
        except ToolInputError:
            raise
        except ZeroDivisionError as exc:
            raise ToolInputError("Division by zero is undefined") from exc
        except Exception as exc:  # noqa: BLE001
            raise ToolInputError(
                f"Could not evaluate expression: {raw!r}. "
                "Only numbers and + - * / // % ** ( ) are supported."
            ) from exc

        if isinstance(value, float):
            if abs(value) > 1e15:
                formatted = f"{value:.6e}"
            elif value == int(value):
                formatted = f"{int(value):,}"
            else:
                formatted = f"{value:,.10f}".rstrip("0").rstrip(".")
            result: int | float = value
        else:
            formatted = f"{value:,}"
            result = value

        return {"expression": raw, "result": result, "formatted": formatted}

    # -- internals ---------------------------------------------------------

    def _eval_node(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if isinstance(node.value, bool):
                raise ToolInputError("Booleans are not valid in arithmetic")
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Pow):
                if abs(left) > _MAX_ABS_BASE or abs(right) > _MAX_EXPONENT:
                    raise ToolInputError("Exponent or base too large")
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](self._eval_node(node.operand))
        raise ToolInputError("Expression contains unsupported syntax")
