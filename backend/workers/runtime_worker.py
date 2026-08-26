from __future__ import annotations

import json
import logging
import time

from app.config import get_settings
from app.deps import session_scope
from definition.services.agent_service import AgentService
from domain.events import Event
from infrastructure.redis.event_bus import _client, ensure_consumer_group
from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
from runtime.definition_loader import build_tool_registry, load_runtime_catalog
from runtime.runtime_service import RuntimeContext, RuntimeService

logger = logging.getLogger(__name__)


def _resolve_runtime_for_event(session, event: Event, data: dict) -> RuntimeService | None:
    store = PostgresSkillRunStore(session)
    agent_slug = data.get("agentSlug")
    skill_id = data.get("skillId")

    if event.skill_run_id:
        existing = store.get_run(event.skill_run_id)
        if existing is None:
            return None
        agent_slug = agent_slug or existing.vars.get("_agent_slug")
        skill_id = skill_id or existing.skill_id
    elif isinstance(event.payload.get("conversation_id"), str):
        existing = store.find_waiting_by_conversation(event.payload["conversation_id"])
        if existing is not None:
            agent_slug = agent_slug or existing.vars.get("_agent_slug")
            skill_id = skill_id or existing.skill_id

    if not agent_slug:
        logger.warning("Skipping event — agentSlug missing: %s", data)
        return None

    if not skill_id:
        from app.api.channels.telegram_utils import default_skill_id

        skill_id = default_skill_id(str(agent_slug))
    if not skill_id:
        logger.warning("Skipping event — skillId missing for agent %s", agent_slug)
        return None

    agent_service = AgentService(session)
    publication = agent_service.get_latest_publication(str(agent_slug))
    if publication is None:
        logger.warning("No publication for agent %s", agent_slug)
        return None

    body = publication.body
    catalog = load_runtime_catalog(body, skill_id)
    registry = build_tool_registry(body, agent_id=body.get("id", ""), session=session)
    pg_store = PostgresSkillRunStore(session)
    context = RuntimeContext(
        catalog=catalog,
        registry=registry,
        store=pg_store,
        agent_id=body.get("id", ""),
        agent_slug=str(agent_slug),
        publication_version=publication.version,
        event_log=pg_store,
    )
    return RuntimeService(context)


def process_event_data(raw: dict) -> None:
    data = json.loads(raw["data"])
    event = Event(
        type=data["type"],
        payload=data.get("payload", {}),
        skill_run_id=data.get("skill_run_id") or data.get("skillRunId"),
    )

    with session_scope() as session:
        service = _resolve_runtime_for_event(session, event, data)
        if service is None:
            logger.warning("Skipping event — runtime not resolved: %s", data)
            return
        result = service.route(event)
        logger.info(
            "Processed event %s run=%s state=%s status=%s",
            event.type,
            result.run.id,
            result.run.current_state,
            result.run.status.value,
        )

        for transition in result.trace.transitions:
            for nested in transition.emitted_events:
                nested_event = {
                    "type": nested.type,
                    "payload": nested.payload,
                    "skillRunId": nested.skill_run_id or result.run.id,
                    "agentSlug": service.context.agent_slug,
                    "skillId": service.context.catalog.skill.id,
                }
                from infrastructure.redis.event_bus import publish_event

                publish_event(nested_event)


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
                    process_event_data(fields)
                    client.xack(settings.event_stream, settings.event_consumer_group, message_id)
                except Exception:
                    logger.exception("Failed to process message %s", message_id)
                    time.sleep(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
