from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from definition.services.agent_service import AgentService
from infrastructure.models.tables import AgentRow, UserRow


def require_agent_readable(session: Session, slug: str, user: UserRow) -> AgentRow:
    try:
        return AgentService(session).require_readable(slug, user.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc


def require_agent_writable(session: Session, slug: str, user: UserRow) -> AgentRow:
    try:
        return AgentService(session).require_writable(slug, user.id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Agent not found") from exc
