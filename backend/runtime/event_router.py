from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain.action import ActionDefinition
from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from domain.skill import SkillDefinition
from runtime.action_executor import ActionExecutor
from runtime.fsm_engine import FSMEngine
from runtime.skill_runner import SkillRunner, SkillRunTrace
from runtime.stores.skill_run_store import InMemoryStore, store_find_waiting, store_get_run, store_save_run
from runtime.tool_executor import ToolExecutor
from tools.registry import ToolRegistry


@dataclass
class RuntimeCatalog:
    skill: SkillDefinition
    actions: dict[str, ActionDefinition]
    start_event: str = "channel.message.received"


@dataclass
class RouterResult:
    run: SkillRun
    trace: SkillRunTrace
    created: bool = False


class EventRouter:
    """Find or create a SkillRun and hand the event to SkillRunner."""

    def __init__(
        self,
        catalog: RuntimeCatalog,
        registry: ToolRegistry,
        store: InMemoryStore | None = None,
    ) -> None:
        self.catalog = catalog
        self.registry = registry
        self.store = store or InMemoryStore()
        tool_executor = ToolExecutor(registry)
        action_executor = ActionExecutor(tool_executor)
        self.fsm = FSMEngine(catalog.skill, catalog.actions, action_executor)
        self.runner = SkillRunner(catalog.skill, self.fsm)

    def route(self, event: Event) -> RouterResult:
        run, created = self._resolve_run(event)
        if event.skill_run_id is None:
            event.skill_run_id = run.id

        for key, value in event.payload.items():
            if key not in run.vars or key in ("text", "last_message", "conversation_id"):
                run.vars[key] = value
        if "text" in event.payload:
            run.vars["last_message"] = event.payload["text"]
        self._sync_correlation(run, event)
        run.vars["_last_event_id"] = event.id

        trace = self.runner.handle(run, event)
        store_save_run(self.store, run)
        return RouterResult(
            run=run.model_copy(deep=True),
            trace=trace,
            created=created,
        )

    def _resolve_run(self, event: Event) -> tuple[SkillRun, bool]:
        if event.skill_run_id:
            existing = store_get_run(self.store, event.skill_run_id)
            if existing is not None:
                return existing, False

        conversation_id = event.payload.get("conversation_id")
        if isinstance(conversation_id, str):
            existing = store_find_waiting(self.store, conversation_id)
            if existing is not None:
                return existing, False

        run = SkillRun(
            skill_id=self.catalog.skill.id,
            skill_version=self.catalog.skill.version,
            current_state=self.catalog.skill.initial,
            history=[self.catalog.skill.initial],
            params=self._build_run_params(event),
            vars=self._build_run_vars(event),
        )
        store_save_run(self.store, run)
        return run, True

    def _build_run_params(self, event: Event) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for param in self.catalog.skill.params:
            value = event.payload.get(param.name)
            if value is not None:
                params[param.name] = value
        for key in ("request_id", "conversation_id", "user_id", "entity_id", "parent_run_id"):
            if key in event.payload and key not in params:
                params[key] = event.payload[key]
        return params

    @staticmethod
    def _build_run_vars(event: Event) -> dict[str, Any]:
        vars: dict[str, Any] = {}
        for key in ("request_id", "conversation_id", "user_id", "entity_id", "parent_run_id"):
            if key in event.payload:
                vars[key] = event.payload[key]
        return vars

    @staticmethod
    def _sync_correlation(run: SkillRun, event: Event) -> None:
        corr = event.correlation
        values = {
            "request_id": corr.request_id,
            "conversation_id": corr.conversation_id,
            "user_id": corr.user_id,
            "entity_id": corr.entity_id,
            "parent_run_id": corr.parent_run_id,
        }
        for key, value in values.items():
            if value:
                run.params[key] = value
                run.vars[key] = value
        for key in values:
            if key in event.payload:
                run.params[key] = event.payload[key]
                run.vars[key] = event.payload[key]


__all__ = ["EventRouter", "InMemoryStore", "RuntimeCatalog", "RouterResult"]
