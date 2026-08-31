from __future__ import annotations

from typing import Any

from definition.mappers.event_mapper import create_domain_event
from domain.events import Event

BUILTIN_EVENT_TYPES: dict[str, dict[str, Any]] = {
    "channel.message.received": {
        "version": "1.0",
        "source": "channel",
        "description": "Входящее сообщение пользователя",
        "required_payload": ["conversation_id"],
    },
    "channel.message.sent": {
        "version": "1.0",
        "source": "channel",
        "description": "Исходящее сообщение пользователю",
        "required_payload": ["conversation_id", "text"],
    },
    "supplier.reply.received": {
        "version": "1.0",
        "source": "supplier",
        "description": "Ответ поставщика",
        "required_payload": ["conversation_id"],
    },
    "request.created": {
        "version": "1.0",
        "source": "crm",
        "description": "Создана заявка",
        "required_payload": ["request_id"],
    },
    "request.updated": {
        "version": "1.0",
        "source": "crm",
        "description": "Обновлена заявка",
        "required_payload": ["request_id"],
    },
    "invoice.received": {
        "version": "1.0",
        "source": "crm",
        "description": "Получен счёт",
        "required_payload": ["request_id"],
    },
    "human.request.approved": {
        "version": "1.0",
        "source": "human",
        "description": "Человек одобрил заявку",
        "required_payload": ["request_id"],
    },
    "human.request.corrected": {
        "version": "1.0",
        "source": "human",
        "description": "Человек внёс правки",
        "required_payload": ["request_id"],
    },
    "shipment.updated": {
        "version": "1.0",
        "source": "crm",
        "description": "Обновлена поставка",
        "required_payload": ["entity_id"],
    },
    "timer.elapsed": {
        "version": "1.0",
        "source": "scheduler",
        "description": "Сработал таймер",
        "required_payload": [],
    },
}


def get_event_type_def(event_type: str) -> dict[str, Any] | None:
    return BUILTIN_EVENT_TYPES.get(event_type)


def validate_event_envelope(event: Event) -> list[str]:
    issues: list[str] = []
    if not event.id:
        issues.append("missing id")
    if not event.type:
        issues.append("missing type")
    if not event.version:
        issues.append("missing version")
    if not event.source:
        issues.append("missing source")
    if not event.timestamp:
        issues.append("missing timestamp")

    type_def = get_event_type_def(event.type)
    if type_def:
        for field in type_def.get("required_payload", []):
            if field not in event.payload:
                issues.append(f"payload missing required field '{field}'")
    return issues


def channel_message_received(
    *,
    conversation_id: str,
    text: str,
    source: str = "channel",
    message_id: str | None = None,
    sender_id: str | None = None,
    skill_run_id: str | None = None,
    causation_id: str | None = None,
    tool_instance_id: str | None = None,
    tool_type_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Event:
    payload: dict[str, Any] = {
        "conversation_id": conversation_id,
        "text": text,
    }
    if message_id:
        payload["message_id"] = message_id
    if sender_id:
        payload["sender_id"] = sender_id
    event_metadata = dict(metadata or {})
    if tool_instance_id:
        event_metadata["tool_instance_id"] = tool_instance_id
    if tool_type_id:
        event_metadata["tool_type_id"] = tool_type_id
    return create_domain_event(
        "channel.message.received",
        source=source,
        payload=payload,
        correlation={"conversation_id": conversation_id},
        skill_run_id=skill_run_id,
        causation_id=causation_id,
        metadata=event_metadata,
    )


def channel_message_sent(
    *,
    conversation_id: str,
    text: str,
    source: str = "channel",
    message_id: str | None = None,
    skill_run_id: str | None = None,
    causation_id: str | None = None,
) -> Event:
    payload: dict[str, Any] = {
        "conversation_id": conversation_id,
        "text": text,
    }
    if message_id:
        payload["message_id"] = message_id
    return create_domain_event(
        "channel.message.sent",
        source=source,
        payload=payload,
        correlation={"conversation_id": conversation_id},
        skill_run_id=skill_run_id,
        causation_id=causation_id,
    )
