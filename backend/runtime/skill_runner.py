from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from domain.skill import SkillDefinition
from runtime.fsm_engine import AUTO_EVENT, FSMEngine, TransitionResult


@dataclass
class SkillRunTrace:
    skill_run_id: str
    states: list[str] = field(default_factory=list)
    transitions: list[TransitionResult] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    status: SkillRunStatus = SkillRunStatus.running
    error: str | None = None


class SkillRunner:
    def __init__(self, skill: SkillDefinition, fsm: FSMEngine) -> None:
        self.skill = skill
        self.fsm = fsm

    def handle(self, run: SkillRun, event: Event) -> SkillRunTrace:
        trace = SkillRunTrace(skill_run_id=run.id, states=list(run.history))
        run.status = SkillRunStatus.running
        run.error = None

        try:
            self._step(run, event, trace)
            self._drain_auto(run, trace)
            self._finalize_status(run)
        except Exception as exc:  # noqa: BLE001 — surface to SkillRun
            run.status = SkillRunStatus.error
            run.error = str(exc)
            trace.error = str(exc)

        trace.status = run.status
        trace.states = list(run.history)
        return trace

    def _step(self, run: SkillRun, event: Event, trace: SkillRunTrace) -> None:
        state = self.skill.get_state(run.current_state)
        if state is None:
            raise KeyError(f"Unknown state '{run.current_state}'")

        transition = self.fsm.find_transition(state, event, run.vars)
        if transition is None:
            if event.type == AUTO_EVENT:
                return
            raise RuntimeError(
                f"No transition for event '{event.type}' in state '{run.current_state}'"
            )

        result = self.fsm.apply_transition(run, transition, event)
        trace.transitions.append(result)
        trace.tool_calls.extend(result.tool_calls)

    def _drain_auto(self, run: SkillRun, trace: SkillRunTrace) -> None:
        """Fire empty/runtime.continue transitions until blocked or final."""
        for _ in range(32):
            state = self.skill.get_state(run.current_state)
            if state is None or state.final:
                return
            auto = Event(type=AUTO_EVENT, skill_run_id=run.id)
            transition = self.fsm.find_transition(state, auto, run.vars)
            if transition is None:
                return
            result = self.fsm.apply_transition(run, transition, auto)
            trace.transitions.append(result)
            trace.tool_calls.extend(result.tool_calls)

    def _finalize_status(self, run: SkillRun) -> None:
        state = self.skill.get_state(run.current_state)
        if state is None:
            run.status = SkillRunStatus.error
            run.error = f"Unknown state '{run.current_state}'"
            return
        if state.final:
            run.status = SkillRunStatus.completed
        else:
            run.status = SkillRunStatus.waiting
