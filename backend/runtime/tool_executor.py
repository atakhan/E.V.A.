from __future__ import annotations

from typing import Any

from domain.events import ToolResult
from tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        tool_id: str,
        command: str,
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolResult:
        tool = self.registry.require(tool_id)
        return tool.handle(command, args, context)
