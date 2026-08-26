from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Event(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    skill_run_id: str | None = None
    id: str = Field(default_factory=lambda: str(uuid4()))


class ToolResult(BaseModel):
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    error: str | None = None


class ActionResult(BaseModel):
    action_id: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    error: str | None = None
