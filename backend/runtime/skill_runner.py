from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from definition.mappers.event_mapper import create_domain_event
from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from domain.skill import SkillDefinition
from runtime.fsm_engine import AUTO_EVENT, FSMEngine, TransitionResult, action_completed_event_type


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
        if run.status == SkillRunStatus.cancelled:
            trace.status = SkillRunStatus.cancelled
            return trace

        run.status = SkillRunStatus.running
        run.error = None

        try:
            pending: list[Event] = [event]
            seen = 0
            while pending and seen < 64:
                current = pending.pop(0)
                result = self._step(run, current, trace)
                seen += 1
                if run.vars.get("_needs_human"):
                    run.status = SkillRunStatus.waiting
                    run.vars.pop("_needs_human", None)
                    trace.status = run.status
                    trace.states = list(run.history)
                    return trace
                for action_id, data in result.action_completions:
                    pending.append(
                        create_domain_event(
                            action_completed_event_type(action_id),
                            source="runtime",
                            payload={"result": data, "action_id": action_id},
                            skill_run_id=run.id,
                            causation_id=run.vars.get("_last_event_id"),
                            action_run_id=run.vars.get("_last_action_run_id"),
                        )
                    )
            self._drain_auto(run, trace)
            self._finalize_status(run)
        except Exception as exc:  # noqa: BLE001 — surface to SkillRun
            run.status = SkillRunStatus.error
            run.error = str(exc)
            trace.error = str(exc)

        trace.status = run.status
        trace.states = list(run.history)
        return trace

    def _step(self, run: SkillRun, event: Event, trace: SkillRunTrace) -> TransitionResult:
        state = self.skill.get_state(run.current_state)
        if state is None:
            raise KeyError(f"Unknown state '{run.current_state}'")

        transition = self.fsm.find_transition(state, event, run.vars)
        if transition is None:
            if event.type == AUTO_EVENT or event.type.startswith("action."):
                return TransitionResult(
                    from_state=run.current_state,
                    to_state=run.current_state,
                    event=event.type,
                )
            raise RuntimeError(
                f"No transition for event '{event.type}' in state '{run.current_state}'"
            )

        result = self.fsm.apply_transition(run, transition, event)
        trace.transitions.append(result)
        trace.tool_calls.extend(result.tool_calls)
        return result

    def _drain_auto(self, run: SkillRun, trace: SkillRunTrace) -> None:
        """Legacy: fire runtime.continue transitions until blocked or final."""
        for _ in range(32):
            state = self.skill.get_state(run.current_state)
            if state is None or state.final:
                return
            auto = create_domain_event(
                AUTO_EVENT,
                source="runtime",
                skill_run_id=run.id,
                causation_id=run.vars.get("_last_event_id"),
            )
            transition = self.fsm.find_transition(state, auto, run.vars)
            if transition is None:
                return
            result = self.fsm.apply_transition(run, transition, auto)
            trace.transitions.append(result)
            trace.tool_calls.extend(result.tool_calls)
            for action_id, data in result.action_completions:
                completion = create_domain_event(
                    action_completed_event_type(action_id),
                    source="runtime",
                    payload={"result": data, "action_id": action_id},
                    skill_run_id=run.id,
                    causation_id=run.vars.get("_last_event_id"),
                )
                try:
                    self._step(run, completion, trace)
                except RuntimeError:
                    pass

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
