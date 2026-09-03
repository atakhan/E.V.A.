from __future__ import annotations

from typing import Any

from app.config import get_settings


def default_skill_id(agent_slug: str) -> str | None:
    """Deprecated. Prefer defaultSkillId on the agent document or event-based routing."""
    from runtime.skill_resolver import env_default_skill_id

    return env_default_skill_id(agent_slug)


def normalize_telegram_update(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return None

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return None

    text = message.get("text") or message.get("caption") or ""
    return {
        "conversation_id": f"tg:chat:{chat_id}",
        "text": text,
        "telegram_chat_id": chat_id,
        "telegram_message_id": message.get("message_id"),
        "telegram_from_id": (message.get("from") or {}).get("id"),
    }
