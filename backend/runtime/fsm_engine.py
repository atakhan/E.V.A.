from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.action import ActionDefinition
from domain.agent import SkillRun
from domain.events import Event
from domain.skill import FsmState, FsmTransition, SkillDefinition
from runtime.action_executor import ActionExecutor
from runtime.guards import evaluate_guard

AUTO_EVENT = "runtime.continue"


@dataclass
class TransitionResult:
    from_state: str
    to_state: str
    event: str
    actions: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    emitted_events: list[Event] = field(default_factory=list)


class FSMEngine:
    def __init__(
        self,
        skill: SkillDefinition,
        actions: dict[str, ActionDefinition],
        action_executor: ActionExecutor,
    ) -> None:
        self.skill = skill
        self.actions = actions
        self.action_executor = action_executor

    def find_transition(
        self,
        state: FsmState,
        event: Event,
        vars: dict[str, Any],
    ) -> FsmTransition | None:
        for transition in state.transitions:
            if not self._event_matches(transition.event, event.type):
                continue
            if evaluate_guard(transition.guard, vars=vars, payload=event.payload):
                return transition
        return None

    @staticmethod
    def _event_matches(transition_event: str, incoming: str) -> bool:
        if transition_event == incoming:
            return True
        # Auto-continue matches empty or explicit runtime.continue transitions
        if incoming == AUTO_EVENT and transition_event in ("", AUTO_EVENT):
            return True
        return False

    def apply_transition(
        self,
        run: SkillRun,
        transition: FsmTransition,
        event: Event,
    ) -> TransitionResult:
        tool_calls: list[dict[str, Any]] = []
        emitted: list[Event] = []

        for action_id in transition.actions:
            tool_calls.extend(self._run_action(run, action_id, emitted))

        from_state = run.current_state
        run.record_state(transition.to)
        tool_calls.extend(self._run_on_enter(run, emitted))

        return TransitionResult(
            from_state=from_state,
            to_state=transition.to,
            event=event.type,
            actions=list(transition.actions),
            tool_calls=tool_calls,
            emitted_events=emitted,
        )

    def _run_action(
        self,
        run: SkillRun,
        action_id: str,
        emitted: list[Event],
    ) -> list[dict[str, Any]]:
        action = self.actions.get(action_id)
        if action is None:
            raise KeyError(f"Unknown action '{action_id}'")
        result = self.action_executor.execute(
            action,
            vars=run.vars,
            skill_run_id=run.id,
        )
        emitted.extend(result.events)
        if not result.ok:
            raise RuntimeError(result.error or f"Action '{action_id}' failed")
        return list(result.tool_calls)

    def _run_on_enter(self, run: SkillRun, emitted: list[Event]) -> list[dict[str, Any]]:
        state = self.skill.get_state(run.current_state)
        if state is None:
            raise KeyError(f"Unknown state '{run.current_state}'")

        tool_calls: list[dict[str, Any]] = []
        for action_id in state.on_enter:
            tool_calls.extend(self._run_action(run, action_id, emitted))
        return tool_calls
