from __future__ import annotations

from typing import Any

from domain.events import Event, ToolResult
from tools.base import BaseTool


class TelegramStubTool(BaseTool):
    id = "telegram"
    commands = ("send_message",)

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def cmd_send_message(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        message = {
            "chat_id": args.get("chat_id") or context.get("vars", {}).get("conversation_id"),
            "text": args.get("text", ""),
        }
        self.sent.append(message)
        return ToolResult(
            ok=True,
            data={"sent": message},
            events=[
                Event(
                    type="telegram.message.sent",
                    payload=message,
                    skill_run_id=context.get("skill_run_id"),
                )
            ],
        )
