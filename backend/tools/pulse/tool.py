from __future__ import annotations

from typing import Any

from domain.events import ToolResult
from tools.base import BaseTool
from tools.pulse.inspect import connectors_snapshot, self_snapshot
from tools.pulse.manifest import PULSE_TOOL_ID


class PulseTool(BaseTool):
    """Self-awareness: who am I, and which connectors are available."""

    id = PULSE_TOOL_ID
    commands = ("self", "connectors")

    def __init__(self, *, agent_body: dict[str, Any] | None = None) -> None:
        self.agent_body = dict(agent_body or {})

    def cmd_self(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        data = self_snapshot(self.agent_body, context)
        return ToolResult(ok=True, data={**data, "self": data})

    def cmd_connectors(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        return ToolResult(ok=True, data=connectors_snapshot(self.agent_body))
