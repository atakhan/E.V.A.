from __future__ import annotations

from domain.events import Event


def event_lock_key(event: Event, *, skill_id: str | None = None) -> str:
    """Lock granularity: one skill on one conversation, not the whole voice thread.

    When conversation and skill are known, inbound and targeted completions share
    ``conv-skill:{conversation}:{skill}`` so two chats serialize (no forked
    razgovor) and a completion cannot race the next replica of the same skill.
    Chat vs parse use different skill ids and do not share a lock.

    Fallback without a skill id: ``run:{skill_run_id}``, else entity, else the event.
    """
    conversation_id = event.payload.get("conversation_id") or event.correlation.conversation_id
    if isinstance(conversation_id, str) and conversation_id and skill_id:
        return f"conv-skill:{conversation_id}:{skill_id}"
    if event.skill_run_id:
        return f"run:{event.skill_run_id}"
    entity = (
        event.payload.get("entity_id")
        or event.correlation.entity_id
        or event.payload.get("request_id")
        or event.correlation.request_id
    )
    if isinstance(entity, str) and entity:
        return f"entity:{entity}"
    return f"event:{event.id}"
