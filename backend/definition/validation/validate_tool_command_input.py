from __future__ import annotations

from definition.catalog.builtin_tools import get_command_input_schema
from definition.catalog.field_schema import validate_fields


def validate_command_input(tool_type_id: str, command_id: str, input_data: dict | None) -> list[str]:
    schema = get_command_input_schema(tool_type_id, command_id)
    if not schema:
        return []
    errors, warnings = validate_fields(schema, input_data or {}, prefix=f"{tool_type_id}.{command_id}.")
    # warnings are returned as non-blocking in agent validation
    return errors + [f"warning: {item}" for item in warnings]


def validate_command_input_errors_only(tool_type_id: str, command_id: str, input_data: dict | None) -> list[str]:
    schema = get_command_input_schema(tool_type_id, command_id)
    if not schema:
        return []
    errors, _warnings = validate_fields(schema, input_data or {}, prefix=f"{tool_type_id}.{command_id}.")
    return errors
