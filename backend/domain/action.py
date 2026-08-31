from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ActionPolicy = Literal["auto", "needs_human"]


class ActionRecipeStep(BaseModel):
    id: str = ""
    tool: str
    command: str
    input: dict[str, Any] = Field(default_factory=dict)
    when: str = ""


class ActionDefinition(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    policy: ActionPolicy = "auto"
    on_failure: str = "fail"
    retry: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")
    recipe: list[ActionRecipeStep] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
