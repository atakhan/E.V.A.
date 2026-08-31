from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def new_event_id() -> str:
    return f"evt_{uuid4()}"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventCorrelation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    conversation_id: str | None = None
    entity_id: str | None = None
    skill_run_id: str | None = Field(default=None, alias="skillRunId")
    action_run_id: str | None = Field(default=None, alias="actionRunId")
    agent_id: str | None = Field(default=None, alias="agentId")
    request_id: str | None = None
    parent_run_id: str | None = Field(default=None, alias="parentRunId")
    user_id: str | None = None


class Event(BaseModel):
    """Domain Event envelope per EVENT_SPEC v0.1."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_event_id)
    type: str
    version: str = "1.0"
    source: str = "system"
    timestamp: str = Field(default_factory=utcnow_iso)
    correlation: EventCorrelation = Field(default_factory=EventCorrelation)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    causation_id: str | None = Field(default=None, alias="causationId")
    skill_run_id: str | None = Field(default=None, alias="skillRunId")

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = dict(data)
        correlation = dict(raw.get("correlation") or {})
        skill_run_id = raw.pop("skill_run_id", None) or raw.pop("skillRunId", None)
        if skill_run_id:
            correlation.setdefault("skill_run_id", skill_run_id)

        payload = raw.get("payload")
        if isinstance(payload, dict):
            for key in (
                "conversation_id",
                "request_id",
                "user_id",
                "entity_id",
                "parent_run_id",
            ):
                if key in payload and key not in correlation:
                    correlation[key] = payload[key]

        if correlation:
            raw["correlation"] = correlation
        return raw

    @model_validator(mode="after")
    def _sync_skill_run_id(self) -> Event:
        if self.skill_run_id and not self.correlation.skill_run_id:
            self.correlation.skill_run_id = self.skill_run_id
        elif self.correlation.skill_run_id and not self.skill_run_id:
            self.skill_run_id = self.correlation.skill_run_id
        return self


class ToolResult(BaseModel):
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    events: list[Event] = Field(default_factory=list)
    error: str | None = None
    tool_execution_id: str | None = None


class ActionResult(BaseModel):
    action_id: str
    ok: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    error: str | None = None
    action_run_id: str | None = None
    needs_human: bool = False
