from __future__ import annotations

from typing import Any

from definition.services.agent_service import AgentService
from infrastructure.models.tables import AgentPublicationRow
from infrastructure.stores.postgres_action_run_store import PostgresActionRunStore
from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
from infrastructure.stores.postgres_tool_execution_store import PostgresToolExecutionStore
from runtime.definition_loader import build_tool_registry, credential_bindings, load_runtime_catalog
from runtime.runtime_service import RuntimeContext, RuntimeService
from sqlalchemy.orm import Session


def resolve_publication(
    agent_service: AgentService,
    agent_slug: str,
    publication_version: str | None,
) -> AgentPublicationRow | None:
    if publication_version:
        return agent_service.get_publication(agent_slug, publication_version)
    return agent_service.get_latest_publication(agent_slug)


def build_runtime_service(
    session: Session,
    *,
    agent_slug: str,
    skill_id: str,
    publication_version: str | None = None,
) -> RuntimeService:
    agent_service = AgentService(session)
    publication = resolve_publication(agent_service, agent_slug, publication_version)
    if publication is None:
        raise KeyError(f"No publication for agent '{agent_slug}' version={publication_version!r}")

    body = publication.body
    catalog = load_runtime_catalog(body, skill_id)
    registry = build_tool_registry(body, agent_id=body.get("id", ""), session=session)
    skill_store = PostgresSkillRunStore(session)
    action_run_store = PostgresActionRunStore(session)
    tool_execution_store = PostgresToolExecutionStore(session)

    context = RuntimeContext(
        catalog=catalog,
        registry=registry,
        store=skill_store,
        agent_id=body.get("id", ""),
        agent_slug=agent_slug,
        publication_version=publication.version,
        publication_body=body,
        event_log=skill_store,
        session=session,
        credential_by_instance=credential_bindings(body),
        agent_body=body,
        action_run_store=action_run_store,
        tool_execution_store=tool_execution_store,
    )
    return RuntimeService(context)


def build_runtime_service_for_publication(
    session: Session,
    *,
    agent_slug: str,
    skill_id: str,
    publication: AgentPublicationRow,
) -> RuntimeService:
    body = publication.body
    catalog = load_runtime_catalog(body, skill_id)
    registry = build_tool_registry(body, agent_id=body.get("id", ""), session=session)
    skill_store = PostgresSkillRunStore(session)
    action_run_store = PostgresActionRunStore(session)
    tool_execution_store = PostgresToolExecutionStore(session)

    context = RuntimeContext(
        catalog=catalog,
        registry=registry,
        store=skill_store,
        agent_id=body.get("id", ""),
        agent_slug=agent_slug,
        publication_version=publication.version,
        publication_body=body,
        event_log=skill_store,
        session=session,
        credential_by_instance=credential_bindings(body),
        agent_body=body,
        action_run_store=action_run_store,
        tool_execution_store=tool_execution_store,
    )
    return RuntimeService(context)
