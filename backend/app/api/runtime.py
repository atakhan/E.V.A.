from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.agent_http import raise_agent_service_error
from definition.services.agent_service import AgentArchivedError, AgentService
from domain.events import Event
from infrastructure.models.tables import SkillRunRow
from infrastructure.stores.postgres_action_run_store import PostgresActionRunStore
from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
from infrastructure.stores.postgres_tool_execution_store import PostgresToolExecutionStore
from runtime.definition_loader import load_runtime_catalog
from runtime.runtime_factory import build_runtime_service
from runtime.skill_run_query import SkillRunListFilters, run_detail_from_row

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class EventPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    type: str
    version: str = "1.0"
    source: str = "runtime"
    timestamp: str | None = None
    correlation: dict[str, Any] | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None
    causation_id: str | None = Field(default=None, alias="causationId")
    skill_run_id: str | None = Field(default=None, alias="skillRunId")


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_slug: str = Field(alias="agentSlug")
    skill_id: str = Field(alias="skillId")
    event: EventPayload


class StartSkillRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_slug: str = Field(alias="agentSlug")
    skill_id: str = Field(alias="skillId")
    publication_version: str | None = Field(default=None, alias="publicationVersion")
    params: dict[str, Any] = Field(default_factory=dict)
    event: EventPayload | None = None


class ExecuteActionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_slug: str = Field(alias="agentSlug")
    skill_id: str = Field(alias="skillId")
    action_id: str = Field(alias="actionId")
    publication_version: str | None = Field(default=None, alias="publicationVersion")
    input: dict[str, Any] = Field(default_factory=dict)


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


def _run_response(result, *, created: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "created": created,
        "skillRunId": result.run.id,
        "agentSlug": result.run.vars.get("_agent_slug"),
        "skillId": result.run.skill_id,
        "status": result.run.status.value,
        "currentState": result.run.current_state,
        "publicationVersion": result.run.skill_version,
        "conversationId": result.run.vars.get("conversation_id"),
        "error": result.run.error,
        "history": result.run.history,
        "toolCalls": result.trace.tool_calls,
        "createdAt": None,
        "updatedAt": None,
    }


def _parse_status_filter(status: list[str] | None) -> tuple[str, ...]:
    if not status:
        return ()
    values: list[str] = []
    for item in status:
        values.extend(part.strip() for part in item.split(",") if part.strip())
    return tuple(values)


def _ensure_agent_active(session: Session, agent_slug: str) -> None:
    try:
        AgentService(session).ensure_active(agent_slug)
    except AgentArchivedError as exc:
        raise_agent_service_error(exc)


@router.post("/runs", response_model=RunResponse)
def create_run(payload: CreateRunRequest, session: Session = Depends(_db_session)) -> dict[str, Any]:
    _ensure_agent_active(session, payload.agent_slug)
    service = build_runtime_service(session, agent_slug=payload.agent_slug, skill_id=payload.skill_id)
    event = Event.model_validate(payload.event.model_dump(by_alias=True, exclude_none=True))
    result = service.route(event)
    return _run_response(result, created=result.created)


@router.post("/runs/start", response_model=RunResponse)
def start_skill(payload: StartSkillRequest, session: Session = Depends(_db_session)) -> dict[str, Any]:
    _ensure_agent_active(session, payload.agent_slug)
    service = build_runtime_service(
        session,
        agent_slug=payload.agent_slug,
        skill_id=payload.skill_id,
        publication_version=payload.publication_version,
    )
    if payload.event is not None:
        event = Event.model_validate(payload.event.model_dump(by_alias=True, exclude_none=True))
        for key, value in payload.params.items():
            event.payload.setdefault(key, value)
    else:
        event = Event(
            type="request.started",
            source="runtime",
            payload=dict(payload.params),
        )
    result = service.route(event)
    return _run_response(result, created=result.created)


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

    service = build_runtime_service(
        session,
        agent_slug=agent_slug,
        skill_id=existing.skill_id,
        publication_version=existing.skill_version,
    )
    event = Event.model_validate(payload.model_dump(by_alias=True, exclude_none=True))
    result = service.route(event)
    return _run_response(result, created=result.created)


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    cancelled = store.cancel_run(run_id)
    if cancelled is None:
        raise HTTPException(status_code=404, detail="Skill run not found")
    return {
        "ok": True,
        "skillRunId": cancelled.id,
        "status": cancelled.status.value,
        "currentState": cancelled.current_state,
    }


@router.get("/runs/by-conversation")
def find_run_by_conversation(
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


@router.get("/runs")
def list_runs(
    agent_slug: str | None = Query(default=None, alias="agentSlug"),
    skill_id: str | None = Query(default=None, alias="skillId"),
    status: list[str] | None = Query(default=None),
    active_only: bool = Query(default=False, alias="activeOnly"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    items, total = store.list_runs(
        SkillRunListFilters(
            agent_slug=agent_slug,
            skill_id=skill_id,
            statuses=_parse_status_filter(status),
            active_only=active_only,
            limit=limit,
            offset=offset,
        )
    )
    return {
        "ok": True,
        "items": [item.to_api() for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    row = session.get(SkillRunRow, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Skill run not found")
    return run_detail_from_row(row)


@router.get("/runs/{run_id}/history")
def get_run_history(run_id: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Skill run not found")

    events = [
        {
            "id": row.id,
            "eventType": row.event_type,
            "payload": row.payload,
            "fromState": row.from_state,
            "toState": row.to_state,
            "toolCalls": row.tool_calls,
            "created": row.created,
            "createdAt": row.created_at.isoformat(),
        }
        for row in store.list_event_logs(run_id)
    ]
    action_runs = PostgresActionRunStore(session).list_for_run(run_id)
    tool_store = PostgresToolExecutionStore(session)
    action_items = []
    for action_run in action_runs:
        tool_execs = tool_store.list_for_action_run(action_run.id)
        action_items.append(
            {
                "id": action_run.id,
                "actionId": action_run.action_id,
                "status": action_run.status.value,
                "output": action_run.output,
                "error": action_run.error,
                "toolExecutions": [
                    {
                        "id": te.id,
                        "toolInstanceId": te.tool_instance_id,
                        "command": te.command,
                        "status": te.status.value,
                        "durationMs": te.duration_ms,
                        "error": te.error,
                    }
                    for te in tool_execs
                ],
            }
        )
    return {
        "ok": True,
        "skillRunId": run_id,
        "events": events,
        "actionRuns": action_items,
    }


@router.post("/runs/{run_id}/replay")
def replay_run(run_id: str, session: Session = Depends(_db_session), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Skill run not found")
    agent_slug = run.vars.get("_agent_slug")
    if not isinstance(agent_slug, str) or not agent_slug:
        raise HTTPException(status_code=400, detail="Skill run has no agent context")

    logs = store.list_event_logs(run_id)
    if offset >= len(logs):
        raise HTTPException(status_code=400, detail="Replay offset out of range")

    service = build_runtime_service(
        session,
        agent_slug=agent_slug,
        skill_id=run.skill_id,
        publication_version=run.skill_version,
    )
    replayed = 0
    for row in logs[offset:]:
        event = Event(type=row.event_type, source="replay", payload=dict(row.payload or {}), skill_run_id=run_id)
        service.route(event)
        replayed += 1
    return {"ok": True, "skillRunId": run_id, "replayed": replayed}


@router.post("/actions/execute")
def execute_action(payload: ExecuteActionRequest, session: Session = Depends(_db_session)) -> dict[str, Any]:
    _ensure_agent_active(session, payload.agent_slug)
    service = build_runtime_service(
        session,
        agent_slug=payload.agent_slug,
        skill_id=payload.skill_id,
        publication_version=payload.publication_version,
    )
    action = service.context.catalog.actions.get(payload.action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    vars = dict(payload.input)
    result = service.fsm.action_executor.execute(action, vars=vars)
    return {
        "ok": result.ok,
        "actionId": payload.action_id,
        "data": result.data,
        "error": result.error,
        "toolCalls": result.tool_calls,
        "actionRunId": result.action_run_id,
    }


@router.get("/metrics")
def runtime_metrics() -> dict[str, Any]:
    from runtime.metrics import snapshot

    return {"ok": True, **snapshot()}


@router.get("/summary")
def runtime_summary(session: Session = Depends(_db_session)) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    agents, totals = store.summarize_runtime()
    return {
        "ok": True,
        "agents": [agent.to_api() for agent in agents],
        "totals": totals.to_api(),
    }


@router.get("/agents/{slug}/summary")
def agent_runtime_summary(slug: str, session: Session = Depends(_db_session)) -> dict[str, Any]:
    store = PostgresSkillRunStore(session)
    summary = store.summarize_agent(slug)
    if summary is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True, **summary.to_api()}
