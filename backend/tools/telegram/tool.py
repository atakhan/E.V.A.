from __future__ import annotations

from typing import Any

import httpx

from definition.catalog.builtin_events import channel_message_sent
from domain.events import ToolResult
from tools.base import BaseTool


def _extract_chat_id(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw)
    if text.startswith("tg:chat:"):
        return text.split(":", 2)[-1]
    return text


class TelegramTool(BaseTool):
    id = "telegram"
    commands = ("send_message",)

    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token

    def cmd_send_message(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        chat_id = _extract_chat_id(args.get("chat_id")) or _extract_chat_id(
            context.get("vars", {}).get("conversation_id")
        )
        text = str(args.get("text", ""))
        if not chat_id:
            return ToolResult(ok=False, error="chat_id is required for telegram.send_message")
        if not text:
            return ToolResult(ok=False, error="text is required for telegram.send_message")

        try:
            response = httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=20.0,
            )
            body = response.json()
        except httpx.HTTPError as exc:
            return ToolResult(ok=False, error=f"Telegram API error: {exc}")

        if not response.is_success or not body.get("ok"):
            description = body.get("description", response.text)
            return ToolResult(ok=False, error=f"Telegram sendMessage failed: {description}")

        result = body.get("result", {})
        message = {
            "chat_id": f"tg:chat:{result.get('chat', {}).get('id', chat_id)}",
            "text": text,
            "telegram_message_id": result.get("message_id"),
        }
        return ToolResult(
            ok=True,
            data={"sent": message},
            events=[
                channel_message_sent(
                    conversation_id=message["chat_id"],
                    text=text,
                    source="telegram",
                    message_id=str(result.get("message_id")) if result.get("message_id") else None,
                    skill_run_id=context.get("skill_run_id"),
                )
            ],
        )
