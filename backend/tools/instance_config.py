from __future__ import annotations

import json
from typing import Any

from definition.catalog.builtin_tools import get_tool_definition


def parse_instance_config(binding: dict[str, Any]) -> dict[str, Any]:
    """Read instance config from binding (config object or legacy configNote JSON)."""
    raw = binding.get("config")
    if isinstance(raw, dict):
        return dict(raw)
    note = binding.get("configNote") or ""
    if isinstance(note, dict):
        return dict(note)
    text = str(note).strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {"note": text}


def get_config_schema(tool_type_id: str) -> list[dict[str, Any]]:
    tool_def = get_tool_definition(tool_type_id)
    if not tool_def:
        return []
    schema = tool_def.get("configSchema")
    return list(schema) if isinstance(schema, list) else []


def merge_config_defaults(tool_type_id: str, config: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for field in get_config_schema(tool_type_id):
        field_id = field.get("id")
        if not field_id:
            continue
        if "default" in field:
            merged[str(field_id)] = field["default"]
    if config:
        merged.update(config)
    return merged


def validate_instance_config(tool_type_id: str, config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    schema = get_config_schema(tool_type_id)
    if not schema:
        return errors
    for field in schema:
        field_id = str(field.get("id") or "")
        if not field_id:
            continue
        value = config.get(field_id)
        if field.get("required") and (value is None or value == ""):
            errors.append(f"config.{field_id} is required")
            continue
        if value is None:
            continue
        field_type = field.get("type", "string")
        if field_type == "integer" and not isinstance(value, int):
            errors.append(f"config.{field_id} must be integer")
        elif field_type == "boolean" and not isinstance(value, bool):
            errors.append(f"config.{field_id} must be boolean")
        elif field_type == "enum":
            options = field.get("enum") or []
            if value not in options:
                errors.append(f"config.{field_id} must be one of {options}")
    return errors
