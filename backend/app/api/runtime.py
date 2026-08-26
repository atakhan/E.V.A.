from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from definition.services.agent_service import AgentService
from domain.events import Event
from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
from runtime.definition_loader import build_tool_registry, load_runtime_catalog
from runtime.runtime_service import RuntimeContext, RuntimeService

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class EventPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    skill_run_id: str | None = Field(default=None, alias="skillRunId")


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_slug: str = Field(alias="agentSlug")
    skill_id: str = Field(alias="skillId")
    event: EventPayload


class RunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
    created: bool
    skill_run_id: str = Field(alias="skillRunId")
    status: str
    current_state: str = Field(alias="currentState")
    history: list[str]
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, alias="toolCalls")


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


def _build_runtime_service(
    session: Session,
    *,
    agent_slug: str,
    skill_id: str,
) -> RuntimeService:
    agent_service = AgentService(session)
    publication = agent_service.get_latest_publication(agent_slug)
    if publication is None:
        raise HTTPException(status_code=404, detail="No published agent version")

    body = publication.body
    catalog = load_runtime_catalog(body, skill_id)
    registry = build_tool_registry(body, agent_id=body.get("id", ""), session=session)
    store = PostgresSkillRunStore(session)
    context = RuntimeContext(
        catalog=catalog,
        registry=registry,
        store=store,
        agent_id=body.get("id", ""),
        agent_slug=agent_slug,
        publication_version=publication.version,
        event_log=store,
    )
    return RuntimeService(context)


@router.post("/runs", response_model=RunResponse)
def create_run(payload: CreateRunRequest, session: Session = Depends(_db_session)) -> dict[str, Any]:
    service = _build_runtime_service(session, agent_slug=payload.agent_slug, skill_id=payload.skill_id)
    event = Event(
        type=payload.event.type,
        payload=payload.event.payload,
        skill_run_id=payload.event.skill_run_id,
    )
    result = service.route(event)
    return {
        "ok": True,
        "created": result.created,
        "skillRunId": result.run.id,
        "status": result.run.status.value,
        "currentState": result.run.current_state,
        "history": result.run.history,
        "toolCalls": result.trace.tool_calls,
    }


@router.post("/events", response_model=RunResponse)
def post_event(payload: EventPayload, session: Session = Depends(_db_session)) -> dict[str, Any]:
    if not payload.skill_run_id:
        raise HTTPException(status_code=400, detail="skillRunId is required")

    store = PostgresSkillRunStore(session)
    existing = store.get_run(payload.skill_run_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Skill run not found")

    agent_slug = existing.vars.get("_agent_slug")
    if not isinstance(agent_slug, str) or not agent_slug:
        raise HTTPException(status_code=400, detail="Skill run has no agent context")

    service = _build_runtime_service(session, agent_slug=agent_slug, skill_id=existing.skill_id)
    event = Event(type=payload.type, payload=payload.payload, skill_run_id=payload.skill_run_id)
    result = service.route(event)
    return {
        "ok": True,
        "created": result.created,
        "skillRunId": result.run.id,
        "status": result.run.status.value,
        "currentState": result.run.current_state,
        "history": result.run.history,
        "toolCalls": result.trace.tool_calls,
    }


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Skill run not found")
    return {
        "ok": True,
        "created": False,
        "skillRunId": run.id,
        "status": run.status.value,
        "currentState": run.current_state,
        "history": run.history,
        "toolCalls": [],
    }


@router.get("/runs")
def find_run(
    conversation_id: str = Query(alias="conversationId"),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    run = store.find_waiting_by_conversation(conversation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Waiting run not found")
    return {
        "ok": True,
        "skillRunId": run.id,
        "status": run.status.value,
        "currentState": run.current_state,
    }
