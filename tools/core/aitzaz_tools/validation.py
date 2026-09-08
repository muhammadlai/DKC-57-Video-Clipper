"""A small, dependency-free JSON-Schema (subset) validator.

Phase 1 tools use a predictable subset of JSON Schema: type, properties,
required, enum, min/max constraints and defaults. This validator covers that
subset with clear error reporting; it can be swapped for the full
``jsonschema`` library later without changing the Tool interface.
"""

from __future__ import annotations

from typing import Any

_TYPES = {
    "object": dict,
    "string": str,
    "boolean": bool,
    "array": list,
}


def _type_matches(expected: str, value: Any) -> bool:
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected in _TYPES:
        return isinstance(value, _TYPES[expected])
    return True  # unknown type keywords are ignored, not failed


def validate_against_schema(
    schema: dict[str, Any], data: Any
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Validate ``data`` against ``schema``.

    Returns ``(cleaned_data, errors)`` where ``cleaned_data`` has defaults
    applied and unknown properties removed for object schemas.
    """
    errors: list[dict[str, str]] = []
    cleaned = _validate(schema, data, "", errors)
    return cleaned, errors


def _validate(schema: dict[str, Any], data: Any, path: str, errors: list) -> Any:
    expected_type = schema.get("type")

    # Apply default when the value is missing entirely.
    if data is None and "default" in schema and not schema.get("required"):
        data = schema["default"]

    if expected_type and not _type_matches(expected_type, data):
        errors.append(
            {"path": path or "$", "message": f"Expected type '{expected_type}'"}
        )
        return data

    if expected_type == "object" and isinstance(data, dict):
        props: dict[str, Any] = schema.get("properties", {})
        required = schema.get("required", [])
        for req in required:
            if req not in data:
                errors.append(
                    {"path": f"{path}.{req}".lstrip("."), "message": "Field is required"}
                )
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if key in props:
                cleaned[key] = _validate(props[key], value, f"{path}.{key}".lstrip("."), errors)
            elif schema.get("additionalProperties", True) is False:
                errors.append(
                    {
                        "path": f"{path}.{key}".lstrip("."),
                        "message": "Unknown field (additionalProperties is false)",
                    }
                )
        for key, subschema in props.items():
            if key not in cleaned and "default" in subschema:
                cleaned[key] = subschema["default"]
        return cleaned

    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(
                {"path": path or "$", "message": f"Must be at least {schema['minLength']} characters"}
            )
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(
                {"path": path or "$", "message": f"Must be at most {schema['maxLength']} characters"}
            )

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(
                {"path": path or "$", "message": f"Must be >= {schema['minimum']}"}
            )
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(
                {"path": path or "$", "message": f"Must be <= {schema['maximum']}"}
            )

    if "enum" in schema and data is not None and data not in schema["enum"]:
        errors.append(
            {
                "path": path or "$",
                "message": f"Must be one of: {', '.join(map(str, schema['enum']))}",
            }
        )

    if expected_type == "array" and isinstance(data, list):
        item_schema = schema.get("items")
        if "minItems" in schema and len(data) < schema["minItems"]:
            errors.append({"path": path or "$", "message": f"Must have at least {schema['minItems']} items"})
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errors.append({"path": path or "$", "message": f"Must have at most {schema['maxItems']} items"})
        if item_schema:
            return [
                _validate(item_schema, item, f"{path}[{i}]", errors)
                for i, item in enumerate(data)
            ]
    return data
