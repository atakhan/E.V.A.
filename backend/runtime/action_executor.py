from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from domain.action import ActionDefinition
from domain.action_run import ActionRun, ActionRunStatus
from domain.events import ActionResult, Event
from infrastructure.stores.postgres_action_run_store import PostgresActionRunStore
from runtime.expression_resolver import build_action_input, resolve_value
from runtime.guards import evaluate_guard
from runtime.tool_executor import ToolExecutor


class ActionExecutionError(Exception):
    def __init__(self, message: str, *, needs_human: bool = False, action_run_id: str | None = None) -> None:
        super().__init__(message)
        self.needs_human = needs_human
        self.action_run_id = action_run_id


class ActionExecutor:
    def __init__(
        self,
        tool_executor: ToolExecutor,
        *,
        resolve_tool_ref: Callable[[str], str] | None = None,
        action_run_store: PostgresActionRunStore | None = None,
    ) -> None:
        self.tool_executor = tool_executor
        self._resolve_tool_ref = resolve_tool_ref
        self._action_run_store = action_run_store

    def execute(
        self,
        action: ActionDefinition,
        *,
        vars: dict[str, Any],
        skill_run_id: str | None = None,
    ) -> ActionResult:
        action_input = build_action_input(vars)
        action_run = ActionRun(
            action_id=action.id,
            action_version=action.version,
            skill_run_id=skill_run_id or "",
            status=ActionRunStatus.running,
            input=action_input,
            started_at=datetime.now(timezone.utc),
        )
        if action.timeout_ms:
            action_run.deadline_at = datetime.now(timezone.utc) + timedelta(milliseconds=action.timeout_ms)

        if self._action_run_store is not None:
            self._action_run_store.create(action_run)

        max_attempts = int(action.retry.get("max_attempts", 1) or 1)
        last_error: str | None = None

        for attempt in range(1, max_attempts + 1):
            action_run.attempt = attempt
            try:
                result = self._execute_once(action, action_run=action_run, vars=vars, action_input=action_input)
                action_run.status = ActionRunStatus.completed
                action_run.output = result.data
                action_run.finished_at = datetime.now(timezone.utc)
                if self._action_run_store is not None:
                    self._action_run_store.update(action_run)
                result.action_run_id = action_run.id
                return result
            except ActionExecutionError as exc:
                last_error = str(exc)
                if exc.needs_human:
                    action_run.status = ActionRunStatus.waiting
                    action_run.error = last_error
                    action_run.finished_at = datetime.now(timezone.utc)
                    if self._action_run_store is not None:
                        self._action_run_store.update(action_run)
                    return ActionResult(
                        action_id=action.id,
                        ok=False,
                        error=last_error,
                        needs_human=True,
                        action_run_id=action_run.id,
                    )
                if attempt >= max_attempts:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if attempt >= max_attempts:
                    break

        on_failure = action.on_failure or ("needs_human" if action.policy == "needs_human" else "fail")
        if on_failure == "needs_human":
            action_run.status = ActionRunStatus.waiting
            action_run.error = last_error
            action_run.finished_at = datetime.now(timezone.utc)
            if self._action_run_store is not None:
                self._action_run_store.update(action_run)
            return ActionResult(
                action_id=action.id,
                ok=False,
                error=last_error,
                needs_human=True,
                action_run_id=action_run.id,
            )

        action_run.status = ActionRunStatus.failed
        action_run.error = last_error
        action_run.finished_at = datetime.now(timezone.utc)
        if self._action_run_store is not None:
            self._action_run_store.update(action_run)
        return ActionResult(
            action_id=action.id,
            ok=False,
            error=last_error or f"Action '{action.id}' failed",
            action_run_id=action_run.id,
        )

    def _execute_once(
        self,
        action: ActionDefinition,
        *,
        action_run: ActionRun,
        vars: dict[str, Any],
        action_input: dict[str, Any],
    ) -> ActionResult:
        merged: dict[str, Any] = {}
        tool_calls: list[dict[str, Any]] = []
        events: list[Event] = []
        step_results: dict[str, dict[str, Any]] = {}
        payload = {
            key: value
            for key, value in vars.items()
            if key in ("conversation_id", "text", "last_message") or not str(key).startswith("_")
        }

        for step in action.recipe:
            if action_run.deadline_at and datetime.now(timezone.utc) > action_run.deadline_at:
                raise ActionExecutionError(f"Action '{action.id}' timed out")

            scope = {
                "input": action_input,
                "vars": vars,
                "steps": step_results,
                "payload": payload,
            }
            if step.when and not evaluate_guard(step.when, vars=scope, payload=payload):
                continue

            step_args = resolve_value(dict(step.input), scope)
            context = {
                "vars": vars,
                "skill_run_id": action_run.skill_run_id,
                "action_id": action.id,
                "action_run_id": action_run.id,
                "action_input": action_input,
                "steps": step_results,
            }
            instance_id = step.tool
            if self._resolve_tool_ref is not None:
                instance_id = self._resolve_tool_ref(step.tool)

            action_run.current_step = step.id or step.command
            if self._action_run_store is not None:
                self._action_run_store.update(action_run)

            max_tool_attempts = int(action.retry.get("max_attempts", 1) or 1)
            result = self.tool_executor.execute(
                instance_id,
                step.command,
                step_args,
                context,
                max_attempts=max_tool_attempts,
            )
            tool_calls.append(
                {
                    "stepId": step.id,
                    "tool": step.tool,
                    "toolInstanceId": instance_id,
                    "command": step.command,
                    "input": step_args,
                    "ok": result.ok,
                    "data": result.data,
                    "error": result.error,
                    "toolExecutionId": result.tool_execution_id,
                }
            )
            events.extend(result.events)
            if not result.ok:
                raise ActionExecutionError(result.error or f"Tool {instance_id}.{step.command} failed")

            step_results[step.id] = {"result": result.data}
            merged.update(result.data)
            for key, value in result.data.items():
                vars[key] = value

        return ActionResult(
            action_id=action.id,
            ok=True,
            data=merged,
            tool_calls=tool_calls,
            events=events,
            action_run_id=action_run.id,
        )
