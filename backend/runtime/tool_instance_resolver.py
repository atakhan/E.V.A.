from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from definition.catalog.builtin_tools import get_tool_definition
from tools.instance_config import parse_instance_config

ResolveStatus = Literal["ok", "unknown", "ambiguous", "disabled"]


@dataclass(frozen=True)
class ResolvedToolInstance:
    instance_id: str
    type_id: str
    binding: dict[str, Any]
    status: ResolveStatus = "ok"


def normalize_tool_instance(raw: dict[str, Any]) -> dict[str, Any] | None:
    tool_id = str(raw.get("toolId") or "").strip()
    if not tool_id or not get_tool_definition(tool_id):
        return None
    instance_id = str(raw.get("id") or tool_id).strip() or tool_id
    name = str(raw.get("name") or "").strip()
    if not name:
        tool_def = get_tool_definition(tool_id)
        name = str(tool_def.get("name") if tool_def else tool_id)
    config = parse_instance_config(raw)
    return {
        "id": instance_id,
        "toolId": tool_id,
        "name": name,
        "enabled": raw.get("enabled") is not False,
        "credentialId": raw.get("credentialId") or None,
        "config": config,
    }


def list_tool_instances(agent_body: dict[str, Any]) -> list[dict[str, Any]]:
    instances: list[dict[str, Any]] = []
    for raw in agent_body.get("tools", []):
        if not isinstance(raw, dict):
            continue
        normalized = normalize_tool_instance(raw)
        if normalized:
            instances.append(normalized)
    return instances


def enabled_instances(agent_body: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in list_tool_instances(agent_body) if item.get("enabled")]


def find_instance_by_id(agent_body: dict[str, Any], instance_id: str) -> dict[str, Any] | None:
    for item in list_tool_instances(agent_body):
        if item["id"] == instance_id:
            return item
    return None


def find_instance_by_credential(agent_body: dict[str, Any], credential_id: str) -> str | None:
    for item in enabled_instances(agent_body):
        if item.get("credentialId") == credential_id:
            return item["id"]
    return None


def instances_by_type(agent_body: dict[str, Any], type_id: str, *, enabled_only: bool = False) -> list[dict[str, Any]]:
    items = enabled_instances(agent_body) if enabled_only else list_tool_instances(agent_body)
    return [item for item in items if item.get("toolId") == type_id]


def resolve_recipe_tool(agent_body: dict[str, Any], tool_ref: str) -> ResolvedToolInstance | None:
    ref = str(tool_ref or "").strip()
    if not ref:
        return None

    by_id = find_instance_by_id(agent_body, ref)
    if by_id:
        if not by_id.get("enabled"):
            return ResolvedToolInstance(
                instance_id=by_id["id"],
                type_id=by_id["toolId"],
                binding=by_id,
                status="disabled",
            )
        return ResolvedToolInstance(
            instance_id=by_id["id"],
            type_id=by_id["toolId"],
            binding=by_id,
        )

    type_def = get_tool_definition(ref)
    if not type_def:
        return None

    enabled = instances_by_type(agent_body, ref, enabled_only=True)
    if len(enabled) == 1:
        item = enabled[0]
        return ResolvedToolInstance(
            instance_id=item["id"],
            type_id=item["toolId"],
            binding=item,
        )
    if len(enabled) > 1:
        return ResolvedToolInstance(
            instance_id=ref,
            type_id=ref,
            binding={},
            status="ambiguous",
        )
  # disabled or missing instance for type
    disabled = instances_by_type(agent_body, ref, enabled_only=False)
    if len(disabled) == 1 and not disabled[0].get("enabled"):
        item = disabled[0]
        return ResolvedToolInstance(
            instance_id=item["id"],
            type_id=item["toolId"],
            binding=item,
            status="disabled",
        )
    return None


def resolve_tool_ref_to_instance_id(agent_body: dict[str, Any], tool_ref: str) -> str | None:
    resolved = resolve_recipe_tool(agent_body, tool_ref)
    if resolved is None or resolved.status in ("ambiguous", "disabled"):
        return None
    return resolved.instance_id


def credential_by_instance(agent_body: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in list_tool_instances(agent_body):
        cred = item.get("credentialId")
        if item.get("enabled") and cred:
            mapping[item["id"]] = str(cred)
    return mapping
