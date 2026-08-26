from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
from runtime.action_executor import ActionExecutor
from runtime.event_router import RuntimeCatalog, RouterResult
from runtime.fsm_engine import FSMEngine
from runtime.skill_runner import SkillRunner, SkillRunTrace
from runtime.stores.skill_run_store import (
    InMemoryStore,
    SkillRunStore,
    store_find_waiting,
    store_get_run,
    store_save_run,
)
from runtime.tool_executor import ToolExecutor
from tools.registry import ToolRegistry


@dataclass
class RuntimeContext:
    catalog: RuntimeCatalog
    registry: ToolRegistry
    store: SkillRunStore | InMemoryStore = field(default_factory=InMemoryStore)
    agent_id: str = ""
    agent_slug: str = ""
    publication_version: str = "0.1.0"
    event_log: PostgresSkillRunStore | None = None


class RuntimeService:
    def __init__(self, context: RuntimeContext) -> None:
        self.context = context
        tool_executor = ToolExecutor(context.registry)
        action_executor = ActionExecutor(tool_executor)
        self.fsm = FSMEngine(context.catalog.skill, context.catalog.actions, action_executor)
        self.runner = SkillRunner(context.catalog.skill, self.fsm)

    def route(self, event: Event) -> RouterResult:
        run, created = self._resolve_run(event)
        if event.skill_run_id is None:
            event.skill_run_id = run.id

        run.vars.setdefault("_agent_id", self.context.agent_id)
        run.vars.setdefault("_agent_slug", self.context.agent_slug)

        for key, value in event.payload.items():
            if key not in run.vars or key in ("text", "last_message", "conversation_id"):
                run.vars[key] = value
        if "text" in event.payload:
            run.vars["last_message"] = event.payload["text"]

        trace = self.runner.handle(run, event)
        store_save_run(self.context.store, run)

        if self.context.event_log is not None:
            last_transition = trace.transitions[-1] if trace.transitions else None
            self.context.event_log.append_event_log(
                run_id=run.id,
                event_type=event.type,
                payload=event.payload,
                from_state=last_transition.from_state if last_transition else run.current_state,
                to_state=last_transition.to_state if last_transition else run.current_state,
                tool_calls=trace.tool_calls,
                created=created,
            )

        return RouterResult(
            run=run.model_copy(deep=True),
            trace=trace,
            created=created,
        )

    def _resolve_run(self, event: Event) -> tuple[SkillRun, bool]:
        if event.skill_run_id:
            existing = store_get_run(self.context.store, event.skill_run_id)
            if existing is not None:
                return existing, False

        conversation_id = event.payload.get("conversation_id")
        if isinstance(conversation_id, str):
            existing = store_find_waiting(self.context.store, conversation_id)
            if existing is not None:
                return existing, False

        run = SkillRun(
            skill_id=self.context.catalog.skill.id,
            skill_version=self.context.publication_version,
            current_state=self.context.catalog.skill.initial,
            history=[self.context.catalog.skill.initial],
            vars={
                "_agent_id": self.context.agent_id,
                "_agent_slug": self.context.agent_slug,
            },
        )
        store_save_run(self.context.store, run)
        return run, True

    def get_run(self, run_id: str) -> SkillRun | None:
        return store_get_run(self.context.store, run_id)
