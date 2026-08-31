from __future__ import annotations

import json
from typing import Any

import redis

from app.config import get_settings
from definition.catalog.builtin_events import validate_event_envelope
from definition.mappers.event_mapper import event_from_wire, event_to_wire
from domain.events import Event

PROCESSED_EVENTS_KEY = "eva:processed_events"


def _client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def is_event_processed(event_id: str) -> bool:
    if not event_id:
        return False
    return bool(_client().sismember(PROCESSED_EVENTS_KEY, event_id))


def mark_event_processed(event_id: str) -> None:
    if not event_id:
        return
    _client().sadd(PROCESSED_EVENTS_KEY, event_id)


def publish_event(
    event: Event | dict[str, Any],
    *,
    agent_slug: str | None = None,
    skill_id: str | None = None,
) -> str:
    settings = get_settings()
    client = _client()

    if isinstance(event, dict):
        domain_event, transport = event_from_wire(event)
        agent_slug = agent_slug or transport.get("agentSlug")
        skill_id = skill_id or transport.get("skillId")
    else:
        domain_event = event

    issues = validate_event_envelope(domain_event)
    if issues:
        raise ValueError(f"Invalid event envelope: {', '.join(issues)}")

    wire = event_to_wire(domain_event, agent_slug=agent_slug, skill_id=skill_id)
    client.xadd(settings.event_stream, {"data": json.dumps(wire)})
    return domain_event.id


def ensure_consumer_group() -> None:
    settings = get_settings()
    client = _client()
    try:
        client.xgroup_create(settings.event_stream, settings.event_consumer_group, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
