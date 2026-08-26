from __future__ import annotations

from pydantic import BaseModel, Field


class ToolCommandDef(BaseModel):
    id: str
    description: str = ""


class ToolDefinition(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    commands: list[ToolCommandDef] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
