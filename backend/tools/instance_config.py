from __future__ import annotations

import json
from typing import Any

from definition.catalog.builtin_tools import get_tool_definition
from definition.catalog.field_schema import apply_defaults, validate_fields


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
    return apply_defaults(get_config_schema(tool_type_id), config)


def validate_instance_config(tool_type_id: str, config: dict[str, Any]) -> list[str]:
    schema = get_config_schema(tool_type_id)
    if not schema:
        return []
    errors, _warnings = validate_fields(schema, config, prefix="config.")
    return errors
