from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from definition.catalog.builtin_tools import BUILTIN_TOOLS
from definition.schemas.agent_api import ToolDefinitionApi

router = APIRouter(prefix="/api/tools", tags=["tools"])


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


@router.get("/catalog", response_model=list[ToolDefinitionApi])
def tool_catalog(_session: Session = Depends(_db_session)) -> list[dict[str, Any]]:
    return BUILTIN_TOOLS
