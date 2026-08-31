from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from domain.events import ToolResult


@runtime_checkable
class Tool(Protocol):
    id: str

    def handle(self, command: str, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """Execute a tool command in the current skill-run context."""


class BaseTool:
    id: str
    tool_type: str = ""
    credential_id: str | None = None
    commands: tuple[str, ...] = ()

    def handle(self, command: str, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        if command not in self.commands:
            return ToolResult(ok=False, error=f"Unknown command '{command}' for tool '{self.id}'")
        method = getattr(self, f"cmd_{command}", None)
        if method is None:
            return ToolResult(ok=False, error=f"Command '{command}' is not implemented on '{self.id}'")
        return method(args, context)
