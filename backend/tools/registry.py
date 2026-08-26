from __future__ import annotations

from tools.base import Tool
from tools.llm_stub import LlmStubTool
from tools.telegram_stub import TelegramStubTool


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.id] = tool

    def get(self, tool_id: str) -> Tool | None:
        return self._tools.get(tool_id)

    def require(self, tool_id: str) -> Tool:
        tool = self.get(tool_id)
        if tool is None:
            raise KeyError(f"Tool '{tool_id}' is not registered")
        return tool

    @classmethod
    def with_stubs(cls) -> ToolRegistry:
        return cls([LlmStubTool(), TelegramStubTool()])
