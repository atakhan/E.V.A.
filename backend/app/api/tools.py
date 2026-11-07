from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.deps import require_user
from definition.catalog.builtin_tools import BUILTIN_TOOLS
from definition.schemas.agent_api import ToolDefinitionApi
from infrastructure.models.tables import UserRow

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("/catalog", response_model=list[ToolDefinitionApi])
def tool_catalog(_user: UserRow = Depends(require_user)) -> list[dict[str, Any]]:
    return BUILTIN_TOOLS
