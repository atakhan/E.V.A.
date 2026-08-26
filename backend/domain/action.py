from __future__ import annotations

from pydantic import BaseModel, Field


class ActionRecipeStep(BaseModel):
    id: str = ""
    tool: str
    command: str
    args: dict[str, object] = Field(default_factory=dict)


class ActionDefinition(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    recipe: list[ActionRecipeStep] = Field(default_factory=list)
