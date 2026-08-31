from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ActionRunStatus(str, Enum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    waiting = "waiting"


class ToolExecutionStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ActionRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    action_version: str = "0.1.0"
    skill_run_id: str
    status: ActionRunStatus = ActionRunStatus.created
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    current_step: str = ""
    error: str | None = None
    attempt: int = 0
    deadline_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ToolExecution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    action_run_id: str
    tool_instance_id: str
    command: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    status: ToolExecutionStatus = ToolExecutionStatus.running
    error: str | None = None
    duration_ms: int | None = None
    attempt: int = 1
