from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.access import require_agent_readable
from app.deps import db_session, require_user
from definition.services.tool_api_log_service import ToolApiLogService
from infrastructure.models.tables import UserRow

router = APIRouter(prefix="/api/agents/{slug}/tool-logs", tags=["tool-logs"])


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
    session: Session = Depends(db_session),
    user: UserRow = Depends(require_user),
) -> dict[str, Any]:
    agent = require_agent_readable(session, slug, user)
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
    session: Session = Depends(db_session),
    user: UserRow = Depends(require_user),
) -> dict[str, Any]:
    agent = require_agent_readable(session, slug, user)
    return ToolApiLogService(session).stats(
        agent.id,
        tool_id=tool_id,
        credential_id=credential_id,
        skill_run_id=skill_run_id,
        hours=hours,
    )
