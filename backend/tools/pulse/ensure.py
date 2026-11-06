from __future__ import annotations

from typing import Any

from tools.pulse.manifest import PULSE_TOOL_ID


def pulse_tool_instance() -> dict[str, Any]:
    return {
        "id": PULSE_TOOL_ID,
        "toolId": PULSE_TOOL_ID,
        "name": "Пульс",
        "enabled": True,
        "config": {},
    }


def ensure_pulse_tool(body: dict[str, Any]) -> dict[str, Any]:
    """Guarantee an enabled Pulse tool instance on the agent draft."""
    tools = [item for item in (body.get("tools") or []) if isinstance(item, dict)]
    if not any(item.get("toolId") == PULSE_TOOL_ID for item in tools):
        tools.append(pulse_tool_instance())
    body["tools"] = tools
    return body
