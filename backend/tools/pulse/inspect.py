"""Build pulse snapshots from an agent document (and optional run context)."""

from __future__ import annotations

from typing import Any

from definition.system_skills import LIFE
from runtime.life import publication_has_life


def _tool_definition(tool_id: str) -> dict | None:
    # Lazy: avoid circular import with builtin_tools → pulse.manifest.
    from definition.catalog.builtin_tools import get_tool_definition

    return get_tool_definition(tool_id)


def _flag(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def self_snapshot(agent_body: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context if isinstance(context, dict) else {}
    vars_ = ctx.get("vars") if isinstance(ctx.get("vars"), dict) else {}
    has_life = publication_has_life(agent_body)
    return {
        "slug": str(agent_body.get("slug") or ""),
        "name": str(agent_body.get("name") or ""),
        "kind": str(agent_body.get("kind") or "library"),
        "description": str(agent_body.get("description") or ""),
        "icon": str(agent_body.get("icon") or ""),
        "alive": has_life,
        "life_skill": has_life,
        "default_skill_id": str(agent_body.get("defaultSkillId") or ""),
        "skill_run_id": str(ctx.get("skill_run_id") or ""),
        "life_run_id": str(vars_.get("_life_run_id") or ""),
        "project_slug": str(agent_body.get("projectSlug") or ""),
        "origin_slug": str(agent_body.get("originSlug") or ""),
    }


def _tool_status(item: dict[str, Any]) -> str:
    tool_id = str(item.get("toolId") or "")
    enabled = _flag(item.get("enabled"), True)
    if not enabled:
        return "disabled"
    definition = _tool_definition(tool_id)
    if definition is None:
        return "unknown_type"
    if definition.get("implemented") is False:
        return "unimplemented"
    if definition.get("credentialKind") and not item.get("credentialId"):
        return "missing_credential"
    return "ready"


def _channel_status(address: dict[str, Any]) -> str:
    tool_id = str(address.get("toolId") or "").strip()
    if not tool_id:
        return "incomplete"
    definition = _tool_definition(tool_id)
    if definition is None:
        return "unknown_type"
    if definition.get("implemented") is False:
        return "unimplemented"
    config = address.get("config") if isinstance(address.get("config"), dict) else {}
    if tool_id == "agents" and not (address.get("agentSlug") or config.get("agentSlug")):
        # peers may live only in memory; address still counts as configured channel
        return "ready"
    if tool_id == "project" and not str(config.get("projectSlug") or "").strip():
        return "incomplete"
    return "ready"


def connectors_snapshot(agent_body: dict[str, Any]) -> dict[str, Any]:
    world = agent_body.get("world") if isinstance(agent_body.get("world"), dict) else {}
    addresses = world.get("addresses") if isinstance(world.get("addresses"), list) else []
    channels: list[dict[str, Any]] = []
    for raw in addresses:
        if not isinstance(raw, dict):
            continue
        channels.append(
            {
                "id": str(raw.get("id") or ""),
                "toolId": str(raw.get("toolId") or ""),
                "name": str(raw.get("name") or ""),
                "status": _channel_status(raw),
            }
        )

    tools: list[dict[str, Any]] = []
    for raw in agent_body.get("tools") or []:
        if not isinstance(raw, dict):
            continue
        tools.append(
            {
                "id": str(raw.get("id") or ""),
                "toolId": str(raw.get("toolId") or ""),
                "name": str(raw.get("name") or ""),
                "enabled": _flag(raw.get("enabled"), True),
                "status": _tool_status(raw),
            }
        )

    skills: list[dict[str, Any]] = []
    for raw in agent_body.get("skills") or []:
        if not isinstance(raw, dict):
            continue
        skill_id = str(raw.get("id") or "")
        skills.append(
            {
                "id": skill_id,
                "name": str(raw.get("name") or ""),
                "systemRole": str(raw.get("systemRole") or ""),
                "status": "life" if skill_id == LIFE or raw.get("systemRole") == LIFE else "present",
            }
        )

    memory_raw = agent_body.get("memory")
    memory: dict[str, Any]
    if not isinstance(memory_raw, dict) or not memory_raw:
        memory = {"status": "empty", "keys": [], "interaction_peers": 0}
    else:
        interaction = memory_raw.get("interaction") if isinstance(memory_raw.get("interaction"), dict) else {}
        peers = interaction.get("peers") if isinstance(interaction.get("peers"), list) else []
        memory = {
            "status": "present",
            "keys": sorted(str(key) for key in memory_raw.keys()),
            "interaction_peers": len(peers),
            "default_allow_inbound": bool(interaction.get("defaultAllowInbound")),
            "default_allow_outbound": bool(interaction.get("defaultAllowOutbound")),
        }

    def _count(items: list[dict[str, Any]], status: str) -> int:
        return sum(1 for item in items if item.get("status") == status)

    summary = {
        "channels_total": len(channels),
        "channels_ready": _count(channels, "ready"),
        "tools_total": len(tools),
        "tools_ready": _count(tools, "ready"),
        "tools_disabled": _count(tools, "disabled"),
        "skills_total": len(skills),
        "has_life": publication_has_life(agent_body),
        "memory_status": memory["status"],
    }
    return {
        "channels": channels,
        "tools": tools,
        "skills": skills,
        "memory": memory,
        "summary": summary,
    }
