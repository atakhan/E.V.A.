from __future__ import annotations

from typing import Any

VALID_FIELD_TYPES = frozenset(
    {"string", "template", "text", "integer", "boolean", "enum", "json", "string_array"}
)


def _field_id(field: dict[str, Any]) -> str:
    return str(field.get("id") or "")


def coerce_field_value(field: dict[str, Any], raw: Any) -> Any:
    field_type = str(field.get("type") or "string")
    if raw is None:
        return None
    if field_type in {"string", "template", "text"}:
        return str(raw)
    if field_type == "integer":
        if isinstance(raw, bool):
            raise ValueError("boolean is not integer")
        if isinstance(raw, int):
            return raw
        text = str(raw).strip()
        if not text:
            return None
        return int(text)
    if field_type == "boolean":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            lowered = raw.strip().lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no", ""):
                return False
        return bool(raw)
    if field_type == "enum":
        return str(raw)
    if field_type == "json":
        if isinstance(raw, (dict, list)):
            return raw
        if isinstance(raw, str):
            import json

            return json.loads(raw)
        return raw
    if field_type == "string_array":
        if isinstance(raw, list):
            return [str(item) for item in raw]
        if isinstance(raw, str):
            import json

            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        raise ValueError("expected string array")
    return raw


def apply_defaults(schema: list[dict[str, Any]], data: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for field in schema:
        field_id = _field_id(field)
        if not field_id:
            continue
        if "default" in field:
            merged[field_id] = field["default"]
    if data:
        merged.update(data)
    return merged


def validate_fields(
    schema: list[dict[str, Any]],
    data: dict[str, Any] | None,
    *,
    prefix: str = "",
    unknown_as_warning: bool = True,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    payload = data or {}
    known_ids = {_field_id(field) for field in schema if _field_id(field)}

    for field in schema:
        field_id = _field_id(field)
        if not field_id:
            continue
        label = f"{prefix}{field_id}" if prefix else field_id
        value = payload.get(field_id)
        if field.get("required") and (value is None or value == ""):
            errors.append(f"{label} is required")
            continue
        if value is None:
            continue
        field_type = str(field.get("type") or "string")
        if field_type not in VALID_FIELD_TYPES:
            warnings.append(f"{label}: unknown field type '{field_type}'")
            continue
        try:
            coerced = coerce_field_value(field, value)
        except (TypeError, ValueError) as exc:
            errors.append(f"{label}: {exc}")
            continue
        if field_type == "enum":
            options = field.get("enum") or []
            if coerced not in options:
                errors.append(f"{label} must be one of {options}")
        if field_type == "integer" and not isinstance(coerced, int):
            errors.append(f"{label} must be integer")
        if field_type == "boolean" and not isinstance(coerced, bool):
            errors.append(f"{label} must be boolean")

    for key in payload:
        if key not in known_ids:
            msg = f"{prefix}{key}: unknown field"
            if unknown_as_warning:
                warnings.append(msg)
            else:
                errors.append(msg)

    return errors, warnings
