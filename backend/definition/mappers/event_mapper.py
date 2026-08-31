from __future__ import annotations

from typing import Any

from domain.events import Event, EventCorrelation, new_event_id, utcnow_iso

TRANSPORT_KEYS = frozenset({"agentSlug", "skillId", "agent_slug", "skill_id"})
CORRELATION_PAYLOAD_KEYS = frozenset(
    {
        "conversation_id",
        "request_id",
        "user_id",
        "entity_id",
        "parent_run_id",
    }
)


def create_domain_event(
    event_type: str,
    *,
    source: str,
    payload: dict[str, Any] | None = None,
    correlation: dict[str, Any] | None = None,
    skill_run_id: str | None = None,
    action_run_id: str | None = None,
    causation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    version: str = "1.0",
    event_id: str | None = None,
    timestamp: str | None = None,
) -> Event:
    corr = EventCorrelation.model_validate(correlation or {})
    if skill_run_id:
        corr.skill_run_id = skill_run_id
    if action_run_id:
        corr.action_run_id = action_run_id
    return Event(
        id=event_id or new_event_id(),
        type=event_type,
        version=version,
        source=source,
        timestamp=timestamp or utcnow_iso(),
        correlation=corr,
        payload=dict(payload or {}),
        metadata=dict(metadata or {}),
        causation_id=causation_id,
        skill_run_id=corr.skill_run_id,
    )


def sync_correlation_to_payload(event: Event) -> Event:
    payload = dict(event.payload)
    corr = event.correlation.model_dump(exclude_none=True)
    for key, value in corr.items():
        snake_key = _to_snake(key)
        if snake_key in CORRELATION_PAYLOAD_KEYS and snake_key not in payload:
            payload[snake_key] = value
    event.payload = payload
    return event


def event_to_wire(
    event: Event,
    *,
    agent_slug: str | None = None,
    skill_id: str | None = None,
) -> dict[str, Any]:
    body = event.model_dump(by_alias=True, exclude_none=True)
    if agent_slug:
        body["agentSlug"] = agent_slug
    if skill_id:
        body["skillId"] = skill_id
    return body


def event_from_wire(data: dict[str, Any]) -> tuple[Event, dict[str, str]]:
    transport: dict[str, str] = {}
    event_data: dict[str, Any] = {}
    for key, value in data.items():
        if key in TRANSPORT_KEYS:
            if key in ("agentSlug", "agent_slug") and value:
                transport["agentSlug"] = str(value)
            if key in ("skillId", "skill_id") and value:
                transport["skillId"] = str(value)
            continue
        event_data[key] = value

    if "version" not in event_data:
        event_data["version"] = "1.0"
    if "source" not in event_data:
        event_data["source"] = _infer_source(event_data.get("type", ""))
    if "timestamp" not in event_data:
        event_data["timestamp"] = utcnow_iso()
    if "id" not in event_data:
        event_data["id"] = new_event_id()

    event = Event.model_validate(event_data)
    return sync_correlation_to_payload(event), transport


def _infer_source(event_type: str) -> str:
    if not event_type:
        return "system"
    if event_type.startswith("action."):
        return "runtime"
    if event_type.startswith("runtime."):
        return "runtime"
    if event_type.startswith("channel."):
        return "channel"
    if event_type.startswith("human."):
        return "human"
    if event_type.startswith("timer."):
        return "scheduler"
    prefix = event_type.split(".", 1)[0]
    return prefix or "system"


def _to_snake(key: str) -> str:
    if key == "skillRunId":
        return "skill_run_id"
    if key == "actionRunId":
        return "action_run_id"
    if key == "agentId":
        return "agent_id"
    if key == "parentRunId":
        return "parent_run_id"
    if key == "userId":
        return "user_id"
    return key
