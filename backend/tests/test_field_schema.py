from __future__ import annotations

import pytest

from definition.catalog.field_schema import apply_defaults, coerce_field_value, validate_fields


def test_coerce_boolean_and_integer():
    assert coerce_field_value({"id": "x", "type": "boolean"}, "true") is True
    assert coerce_field_value({"id": "x", "type": "integer"}, "42") == 42


def test_apply_defaults():
    schema = [{"id": "count", "type": "integer", "default": 0}]
    assert apply_defaults(schema, {"count": 5})["count"] == 5
    assert apply_defaults(schema, {})["count"] == 0


def test_validate_required_and_unknown():
    schema = [{"id": "text", "type": "string", "required": True}]
    errors, warnings = validate_fields(schema, {})
    assert any("required" in item for item in errors)
    _errors, warnings = validate_fields(schema, {"text": "ok", "extra": 1})
    assert any("unknown field" in item for item in warnings)
