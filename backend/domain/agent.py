from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SkillRunStatus(str, Enum):
    running = "running"
    waiting = "waiting"
    completed = "completed"
    cancelled = "cancelled"
    error = "error"


class AgentDefinition(BaseModel):
    id: str
    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    skill_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)


class SkillRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    skill_id: str
    skill_version: str = "0.1.0"
    current_state: str
    status: SkillRunStatus = SkillRunStatus.running
    params: dict[str, Any] = Field(default_factory=dict)
    vars: dict[str, Any] = Field(default_factory=dict)
    history: list[str] = Field(default_factory=list)
    error: str | None = None
    revision: int = 0
    expires_at: str | None = None

    def record_state(self, state_id: str) -> None:
        self.current_state = state_id
        self.history.append(state_id)
