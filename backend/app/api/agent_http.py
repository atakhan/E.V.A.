from __future__ import annotations

from fastapi import HTTPException

from definition.services.agent_service import AgentArchivedError, AgentProtectedError


def raise_agent_service_error(exc: Exception) -> None:
    if isinstance(exc, AgentArchivedError):
        raise HTTPException(status_code=409, detail="Agent is archived") from exc
    if isinstance(exc, AgentProtectedError):
        raise HTTPException(status_code=403, detail="Agent is protected") from exc
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise exc
