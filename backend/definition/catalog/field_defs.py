from __future__ import annotations

from typing import Any


def field(
    field_id: str,
    *,
    type: str = "string",
    required: bool = False,
    default: Any = None,
    scope: str = "call",
    enum: list[Any] | None = None,
    label: str | None = None,
    placeholder: str | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": field_id,
        "type": type,
        "required": required,
        "scope": scope,
    }
    if default is not None:
        item["default"] = default
    if enum is not None:
        item["enum"] = enum
    ui: dict[str, str] = {}
    if label:
        ui["label"] = label
    if placeholder:
        ui["placeholder"] = placeholder
    if group:
        ui["group"] = group
    if ui:
        item["ui"] = ui
    return item


def config_field(
    field_id: str,
    *,
    type: str = "string",
    required: bool = False,
    default: Any = None,
    enum: list[Any] | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    return field(
        field_id,
        type=type,
        required=required,
        default=default,
        scope="instance",
        enum=enum,
        label=label,
    )
