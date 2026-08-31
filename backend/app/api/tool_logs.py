from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from definition.services.tool_api_log_service import ToolApiLogService
from infrastructure.models.tables import AgentRow

router = APIRouter(prefix="/api/agents/{slug}/tool-logs", tags=["tool-logs"])


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


def _require_agent(session: Session, slug: str) -> AgentRow:
    agent = session.scalar(select(AgentRow).where(AgentRow.slug == slug))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("")
def list_agent_tool_logs(
    slug: str,
    tool_id: str | None = Query(default=None, alias="toolId"),
    credential_id: str | None = Query(default=None, alias="credentialId"),
    command: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skill_run_id: str | None = Query(default=None, alias="skillRunId"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    agent = _require_agent(session, slug)
    return ToolApiLogService(session).list_logs(
        agent.id,
        tool_id=tool_id,
        credential_id=credential_id,
        command=command,
        status=status,
        skill_run_id=skill_run_id,
        limit=limit,
        offset=offset,
    )


@router.get("/stats")
def agent_tool_log_stats(
    slug: str,
    tool_id: str | None = Query(default=None, alias="toolId"),
    credential_id: str | None = Query(default=None, alias="credentialId"),
    skill_run_id: str | None = Query(default=None, alias="skillRunId"),
    hours: int | None = Query(default=None, ge=1, le=24 * 90),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    agent = _require_agent(session, slug)
    return ToolApiLogService(session).stats(
        agent.id,
        tool_id=tool_id,
        credential_id=credential_id,
        skill_run_id=skill_run_id,
        hours=hours,
    )
