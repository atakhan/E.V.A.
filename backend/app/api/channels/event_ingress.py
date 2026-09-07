from __future__ import annotations

from typing import Any

from app.api.channels.web_act import normalize_web_act
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
    metadata: dict[str, Any] | None = None,
    actor_id: str | None = None,
    focus: dict[str, Any] | None = None,
    intent: str | None = None,
    entity_ids: list[Any] | None = None,
) -> dict[str, Any]:
    payload, act_meta = normalize_web_act(
        dict(payload),
        actor_id=actor_id,
        focus=focus,
        intent=intent,
        entity_ids=entity_ids,
    )
    conversation_id = str(payload.get("conversation_id") or "")
    text = str(payload.get("text") or payload.get("message") or "")
    event_metadata = {**(metadata or {}), **act_meta}
    event = channel_message_received(
        conversation_id=conversation_id,
        text=text,
        source=source,
        message_id=str(payload["message_id"]) if payload.get("message_id") else None,
        sender_id=str(payload["sender_id"]) if payload.get("sender_id") else None,
        tool_instance_id=tool_instance_id,
        tool_type_id=tool_type_id,
        metadata=event_metadata,
    )
    if event_type != "channel.message.received":
        event.type = event_type
    for key, value in payload.items():
        if key not in event.payload:
            event.payload[key] = value
    user_id = payload.get("user_id")
    if isinstance(user_id, str) and user_id:
        event.correlation.user_id = user_id
    entity_id = payload.get("entity_id")
    if isinstance(entity_id, str) and entity_id:
        event.correlation.entity_id = entity_id
    request_id = payload.get("request_id")
    if isinstance(request_id, str) and request_id:
        event.correlation.request_id = request_id
    message_id = publish_event(event, agent_slug=agent_slug, skill_id=skill_id)
    return {"ok": True, "queued": True, "messageId": message_id, "eventId": event.id}
