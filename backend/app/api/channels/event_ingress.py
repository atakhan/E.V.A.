from __future__ import annotations

from typing import Any

from definition.catalog.builtin_events import channel_message_received
from infrastructure.redis.event_bus import publish_event


def enqueue_channel_event(
    *,
    agent_slug: str,
    payload: dict[str, Any],
    event_type: str = "channel.message.received",
    skill_id: str | None = None,
    source: str = "channel",
    tool_instance_id: str | None = None,
    tool_type_id: str | None = None,
) -> dict[str, Any]:
    conversation_id = str(payload.get("conversation_id") or "")
    text = str(payload.get("text") or payload.get("message") or "")
    event = channel_message_received(
        conversation_id=conversation_id,
        text=text,
        source=source,
        message_id=str(payload["message_id"]) if payload.get("message_id") else None,
        sender_id=str(payload["sender_id"]) if payload.get("sender_id") else None,
        tool_instance_id=tool_instance_id,
        tool_type_id=tool_type_id,
    )
    if event_type != "channel.message.received":
        event.type = event_type
    for key, value in payload.items():
        if key not in event.payload:
            event.payload[key] = value
    message_id = publish_event(event, agent_slug=agent_slug, skill_id=skill_id)
    return {"ok": True, "queued": True, "messageId": message_id, "eventId": event.id}
