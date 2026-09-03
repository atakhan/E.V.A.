from __future__ import annotations

import json
import logging
import time

from app.config import get_settings
from app.deps import session_scope
from definition.mappers.event_mapper import event_from_wire, event_to_wire
from domain.events import Event
from infrastructure.redis.event_bus import (
    _client,
    ensure_consumer_group,
    is_event_processed,
    mark_event_processed,
    publish_event,
)
from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
from runtime.correlation_lock import correlation_lock
from runtime.dlq import increment_attempt, max_delivery_attempts, move_to_dlq
from runtime.exceptions import ConcurrentUpdateError
from runtime.runtime_factory import build_runtime_service
from runtime.scheduler import RuntimeScheduler

logger = logging.getLogger(__name__)


def _pinned_version_for_event(session, event: Event, transport: dict[str, str]) -> str | None:
    store = PostgresSkillRunStore(session)
    if event.skill_run_id:
        existing = store.get_run(event.skill_run_id)
        if existing is not None:
            return existing.skill_version
    conversation_id = event.payload.get("conversation_id")
    if isinstance(conversation_id, str):
        existing = store.find_waiting_by_conversation(conversation_id)
        if existing is not None:
            return existing.skill_version
    return None


def _resolve_runtime_for_event(
    session,
    event: Event,
    transport: dict[str, str],
) -> tuple | None:
    agent_slug = transport.get("agentSlug")
    skill_id = transport.get("skillId")
    store = PostgresSkillRunStore(session)

    if event.skill_run_id:
        existing = store.get_run(event.skill_run_id)
        if existing is None:
            return None
        agent_slug = agent_slug or existing.vars.get("_agent_slug")
        skill_id = existing.skill_id
    elif isinstance(event.payload.get("conversation_id"), str):
        existing = store.find_waiting_by_conversation(event.payload["conversation_id"])
        if existing is not None:
            agent_slug = agent_slug or existing.vars.get("_agent_slug")
            skill_id = existing.skill_id

    if not agent_slug:
        logger.warning("Skipping event — agentSlug missing: %s", event.type)
        return None

    if not skill_id:
        from runtime.skill_resolver import resolve_skill_for_agent_slug

        resolution = resolve_skill_for_agent_slug(
            session,
            agent_slug=str(agent_slug),
            event_type=event.type,
            explicit_skill_id=transport.get("skillId"),
        )
        if not resolution.ok:
            logger.warning(
                "Skipping event — skill routing failed for agent %s event %s: %s",
                agent_slug,
                event.type,
                resolution.error,
            )
            return None
        skill_id = resolution.skill_id

    pinned = _pinned_version_for_event(session, event, transport)
    try:
        service = build_runtime_service(
            session,
            agent_slug=str(agent_slug),
            skill_id=str(skill_id),
            publication_version=pinned,
        )
    except KeyError as exc:
        logger.warning(
            "Skipping event — runtime not resolved for agent %s skill=%s version=%s: %s",
            agent_slug,
            skill_id,
            pinned,
            exc,
        )
        return None
    return service, str(agent_slug), str(skill_id)


def process_event_data(raw: dict, *, message_id: str | None = None) -> None:
    data = json.loads(raw["data"])
    event, transport = event_from_wire(data)

    if is_event_processed(event.id):
        logger.info("Skipping duplicate event %s", event.id)
        return

    correlation_key = (
        event.payload.get("conversation_id")
        or event.correlation.conversation_id
        or event.skill_run_id
        or event.id
    )

    with correlation_lock(str(correlation_key)):
        with session_scope() as session:
            resolved = _resolve_runtime_for_event(session, event, transport)
            if resolved is None:
                logger.warning("Skipping event — runtime not resolved: %s", event.id)
                return
            service, agent_slug, skill_id = resolved

            try:
                results = service.route_all(event)
            except ConcurrentUpdateError as exc:
                logger.warning("Concurrent update for run, will retry: %s", exc)
                raise

            mark_event_processed(event.id)
            from runtime import metrics

            metrics.inc_events_processed(len(results))
            for result in results:
                logger.info(
                    "Processed event %s run=%s state=%s status=%s",
                    event.type,
                    result.run.id,
                    result.run.current_state,
                    result.run.status.value,
                )
                for transition in result.trace.transitions:
                    for nested in transition.emitted_events:
                        publish_event(
                            nested,
                            agent_slug=agent_slug,
                            skill_id=result.run.skill_id,
                        )

            scheduler = RuntimeScheduler(session)
            scheduler.process_due(agent_slug=agent_slug, skill_id=skill_id)


def run_worker(poll_ms: int = 1000) -> None:
    settings = get_settings()
    ensure_consumer_group()
    client = _client()
    consumer = "worker-1"

    logger.info("Runtime worker started on stream %s", settings.event_stream)
    while True:
        messages = client.xreadgroup(
            settings.event_consumer_group,
            consumer,
            {settings.event_stream: ">"},
            count=10,
            block=poll_ms,
        )
        if not messages:
            continue
        for _stream, entries in messages:
            for message_id, fields in entries:
                try:
                    process_event_data(fields, message_id=message_id)
                    client.xack(settings.event_stream, settings.event_consumer_group, message_id)
                except ConcurrentUpdateError:
                    logger.warning("Concurrent update for message %s — leaving in PEL", message_id)
                    time.sleep(0.2)
                except Exception:
                    attempts = increment_attempt(message_id)
                    if attempts >= max_delivery_attempts():
                        move_to_dlq(fields, reason="max_attempts", attempts=attempts)
                        client.xack(settings.event_stream, settings.event_consumer_group, message_id)
                        logger.error("Moved message %s to DLQ after %s attempts", message_id, attempts)
                    else:
                        logger.exception("Failed to process message %s (attempt %s)", message_id, attempts)
                    time.sleep(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
