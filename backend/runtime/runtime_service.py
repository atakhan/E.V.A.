from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from infrastructure.stores.postgres_action_run_store import PostgresActionRunStore
from infrastructure.stores.postgres_tool_execution_store import PostgresToolExecutionStore
from runtime.action_executor import ActionExecutor
from runtime.event_router import RuntimeCatalog, RouterResult
from runtime.fsm_engine import FSMEngine
from runtime.skill_routing import find_skills_for_event
from runtime.skill_runner import SkillRunner, SkillRunTrace
from runtime.stores.skill_run_store import (
    InMemoryStore,
    SkillRunStore,
    store_find_waiting_runs,
    store_get_run,
    store_save_run,
)
from runtime.tool_instance_resolver import resolve_recipe_tool
from runtime.tool_executor import ToolExecutor
from runtime.tool_log_context import ToolLogContext
from tools.registry import ToolRegistry


@dataclass
class RuntimeContext:
    catalog: RuntimeCatalog
    registry: ToolRegistry
    store: SkillRunStore | InMemoryStore = field(default_factory=InMemoryStore)
    agent_id: str = ""
    agent_slug: str = ""
    publication_version: str = "0.1.0"
    publication_body: dict[str, Any] = field(default_factory=dict)
    event_log: Any | None = None
    session: Any | None = None
    credential_by_instance: dict[str, str] = field(default_factory=dict)
    agent_body: dict[str, Any] = field(default_factory=dict)
    action_run_store: PostgresActionRunStore | None = None
    tool_execution_store: PostgresToolExecutionStore | None = None


class RuntimeService:
    def __init__(self, context: RuntimeContext) -> None:
        self.context = context
        log_context = None
        if context.session is not None and context.agent_id:
            log_context = ToolLogContext(
                session=context.session,
                agent_id=context.agent_id,
                agent_slug=context.agent_slug,
                credential_by_instance=context.credential_by_instance,
            )

        def resolve_tool_ref(tool_ref: str) -> str:
            resolved = resolve_recipe_tool(context.agent_body, tool_ref)
            if resolved is None:
                raise KeyError(f"Unknown tool reference '{tool_ref}'")
            if resolved.status == "ambiguous":
                raise KeyError(f"Ambiguous tool reference '{tool_ref}': multiple instances of this type")
            if resolved.status == "disabled":
                raise KeyError(f"Tool instance '{resolved.instance_id}' is disabled")
            return resolved.instance_id

        tool_executor = ToolExecutor(
            context.registry,
            log_context=log_context,
            tool_execution_store=context.tool_execution_store,
        )
        action_executor = ActionExecutor(
            tool_executor,
            resolve_tool_ref=resolve_tool_ref if context.agent_body else None,
            action_run_store=context.action_run_store,
        )
        self.fsm = FSMEngine(
            context.catalog.skill,
            context.catalog.actions,
            action_executor,
        )
        self.runner = SkillRunner(context.catalog.skill, self.fsm)

    def route(self, event: Event) -> RouterResult:
        results = self.route_all(event)
        if not results:
            raise RuntimeError(f"No skill run resolved for event '{event.type}'")
        return results[0]

    def route_all(self, event: Event) -> list[RouterResult]:
        targets = self._resolve_targets(event)
        results: list[RouterResult] = []
        for run, created, service in targets:
            result = service._route_single(run, event, created=created)
            results.append(result)
        return results

    def _route_single(self, run: SkillRun, event: Event, *, created: bool) -> RouterResult:
        if run.status == SkillRunStatus.cancelled:
            return RouterResult(run=run.model_copy(deep=True), trace=SkillRunTrace(skill_run_id=run.id), created=created)

        event_copy = event.model_copy(deep=True)
        if event_copy.skill_run_id is None:
            event_copy.skill_run_id = run.id

        run.vars.setdefault("_agent_id", self.context.agent_id)
        run.vars.setdefault("_agent_slug", self.context.agent_slug)

        for key, value in event_copy.payload.items():
            if key not in run.vars or key in ("text", "last_message", "conversation_id"):
                run.vars[key] = value
        if "text" in event_copy.payload:
            run.vars["last_message"] = event_copy.payload["text"]
        self._sync_correlation(run, event_copy)
        run.vars["_last_event_id"] = event_copy.id

        trace = self.runner.handle(run, event_copy)
        store_save_run(self.context.store, run)

        if self.context.event_log is not None:
            last_transition = trace.transitions[-1] if trace.transitions else None
            self.context.event_log.append_event_log(
                run_id=run.id,
                event_type=event_copy.type,
                payload=event_copy.payload,
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

    def cancel_run(self, run_id: str) -> SkillRun | None:
        run = store_get_run(self.context.store, run_id)
        if run is None:
            return None
        run.status = SkillRunStatus.cancelled
        run.error = None
        if self.context.action_run_store is not None:
            self.context.action_run_store.cancel_active_for_run(run_id)
        store_save_run(self.context.store, run)
        return run

    def _resolve_targets(self, event: Event) -> list[tuple[SkillRun, bool, RuntimeService]]:
        if event.skill_run_id:
            existing = store_get_run(self.context.store, event.skill_run_id)
            if existing is not None:
                return [(existing, False, self)]

        for key in ("conversation_id", "request_id", "entity_id"):
            value = event.payload.get(key) or getattr(event.correlation, key, None)
            if isinstance(value, str) and value:
                waiting = self._find_waiting_runs(key, value)
                if waiting:
                    return [(run, False, self._service_for_run(run)) for run in waiting]

        skill_ids = [self.context.catalog.skill.id]
        if self.context.publication_body:
            discovered = find_skills_for_event(self.context.publication_body, event.type)
            if discovered:
                skill_ids = discovered

        targets: list[tuple[SkillRun, bool, RuntimeService]] = []
        for skill_id in skill_ids:
            service = self if skill_id == self.context.catalog.skill.id else self._service_for_skill(skill_id)
            if service is None:
                continue
            run = SkillRun(
                skill_id=skill_id,
                skill_version=service.context.publication_version,
                current_state=service.context.catalog.skill.initial,
                history=[service.context.catalog.skill.initial],
                params=service._build_run_params(event),
                vars={
                    "_agent_id": service.context.agent_id,
                    "_agent_slug": service.context.agent_slug,
                    **service._build_run_vars(event),
                },
            )
            store_save_run(service.context.store, run)
            targets.append((run, True, service))
        return targets

    def _service_for_run(self, run: SkillRun) -> RuntimeService:
        if run.skill_id == self.context.catalog.skill.id and run.skill_version == self.context.publication_version:
            return self
        return self._service_for_skill(run.skill_id, publication_version=run.skill_version) or self

    def _service_for_skill(
        self,
        skill_id: str,
        *,
        publication_version: str | None = None,
    ) -> RuntimeService | None:
        if self.context.session is None:
            return None
        from runtime.runtime_factory import build_runtime_service

        version = publication_version or self.context.publication_version
        try:
            return build_runtime_service(
                self.context.session,
                agent_slug=self.context.agent_slug,
                skill_id=skill_id,
                publication_version=version,
            )
        except KeyError:
            return None

    def _find_waiting_runs(self, correlation_key: str, value: str) -> list[SkillRun]:
        store = self.context.store
        from runtime.stores.skill_run_store import store_find_waiting_runs

        return store_find_waiting_runs(store, correlation_key, value)

    def _build_run_params(self, event: Event) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for param in self.context.catalog.skill.params:
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

    def get_run(self, run_id: str) -> SkillRun | None:
        return store_get_run(self.context.store, run_id)
