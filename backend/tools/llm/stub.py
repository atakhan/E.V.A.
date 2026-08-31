from __future__ import annotations

from typing import Any

from domain.events import ToolResult
from tools.base import BaseTool


class LlmStubTool(BaseTool):
    id = "llm"
    commands = ("run", "run_structured", "parse_request")

    def cmd_run(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        return ToolResult(ok=True, data={"text": args.get("prompt", "")})

    def cmd_run_structured(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        return ToolResult(ok=True, data={"structured": args.get("schema", {}), "ok": True})

    def cmd_parse_request(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text = str(args.get("text") or context.get("vars", {}).get("last_message", ""))
        needs_clarification = "гриб" in text.lower() or args.get("force_clarification") is True
        return ToolResult(
            ok=True,
            data={
                "parsed": {
                    "raw_text": text,
                    "item": "грибки" if needs_clarification else "материал",
                    "needs_clarification": needs_clarification,
                },
                "needs_clarification": needs_clarification,
            },
        )
