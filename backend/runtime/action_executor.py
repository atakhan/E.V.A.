from __future__ import annotations

import re
from typing import Any

from domain.action import ActionDefinition
from domain.events import ActionResult, Event
from runtime.tool_executor import ToolExecutor

_VAR_RE = re.compile(r"\$\{vars\.([a-zA-Z0-9_]+)\}")


def resolve_args(args: dict[str, Any], vars: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in args.items():
        if isinstance(value, str):

            def repl(match: re.Match[str]) -> str:
                return str(vars.get(match.group(1), ""))

            resolved[key] = _VAR_RE.sub(repl, value)
        else:
            resolved[key] = value
    return resolved


class ActionExecutor:
    def __init__(self, tool_executor: ToolExecutor) -> None:
        self.tool_executor = tool_executor

    def execute(
        self,
        action: ActionDefinition,
        *,
        vars: dict[str, Any],
        skill_run_id: str | None = None,
    ) -> ActionResult:
        merged: dict[str, Any] = {}
        tool_calls: list[dict[str, Any]] = []
        events: list[Event] = []

        for step in action.recipe:
            step_args = resolve_args(dict(step.args), vars)
            context = {
                "vars": vars,
                "skill_run_id": skill_run_id,
                "action_id": action.id,
            }
            result = self.tool_executor.execute(step.tool, step.command, step_args, context)
            tool_calls.append(
                {
                    "tool": step.tool,
                    "command": step.command,
                    "args": step_args,
                    "ok": result.ok,
                    "data": result.data,
                    "error": result.error,
                }
            )
            events.extend(result.events)
            if not result.ok:
                return ActionResult(
                    action_id=action.id,
                    ok=False,
                    data=merged,
                    tool_calls=tool_calls,
                    events=events,
                    error=result.error or f"Tool {step.tool}.{step.command} failed",
                )
            merged.update(result.data)
            # Promote useful flags into vars for subsequent steps / guards
            for key, value in result.data.items():
                vars[key] = value

        return ActionResult(
            action_id=action.id,
            ok=True,
            data=merged,
            tool_calls=tool_calls,
            events=events,
        )
