from __future__ import annotations

from typing import Any

from domain.agent import SkillRun
from domain.events import Event
from runtime.stores.skill_run_store import store_find_waiting_runs


def find_skills_for_event(agent_body: dict[str, Any], event_type: str) -> list[str]:
    """Return skill ids whose initial state handles event_type."""
    matches: list[str] = []
    for skill_doc in agent_body.get("skills", []):
        if not isinstance(skill_doc, dict):
            continue
        skill_id = skill_doc.get("id")
        if not skill_id:
            continue
        initial = skill_doc.get("initial")
        if not initial and skill_doc.get("states"):
            initial = skill_doc["states"][0].get("id")
        for state_doc in skill_doc.get("states", []):
            if state_doc.get("id") != initial:
                continue
            for transition in state_doc.get("transitions", []):
                if transition.get("event") == event_type:
                    matches.append(str(skill_id))
                    break
    return matches


def skill_handles_event_in_state(skill_doc: dict[str, Any], state_id: str, event_type: str) -> bool:
    for state_doc in skill_doc.get("states", []):
        if state_doc.get("id") != state_id:
            continue
        for transition in state_doc.get("transitions", []):
            if transition.get("event") == event_type:
                return True
    return False


def skill_docs_by_id(agent_body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    docs: dict[str, dict[str, Any]] = {}
    for skill_doc in agent_body.get("skills", []):
        if not isinstance(skill_doc, dict):
            continue
        skill_id = skill_doc.get("id")
        if skill_id:
            docs[str(skill_id)] = skill_doc
    return docs


def run_accepts_event(run: SkillRun, event_type: str, agent_body: dict[str, Any]) -> bool:
    """True if this run's current state declares a transition for event_type."""
    doc = skill_docs_by_id(agent_body).get(run.skill_id)
    if doc is None:
        return False
    return skill_handles_event_in_state(doc, run.current_state, event_type)


def waiting_runs_matching_event(
    waiting: list[SkillRun],
    event_type: str,
    agent_body: dict[str, Any],
) -> list[SkillRun]:
    """Waiting/running runs whose current state waits for this event type."""
    return [run for run in waiting if run_accepts_event(run, event_type, agent_body)]


def matching_waiting_run(store: Any, event: Event, agent_body: dict[str, Any] | None) -> SkillRun | None:
    """First waiting/running run on this conversation whose state waits for event.type."""
    if not agent_body:
        return None
    conversation_id = event.payload.get("conversation_id") or event.correlation.conversation_id
    if not isinstance(conversation_id, str) or not conversation_id:
        return None
    waiting = store_find_waiting_runs(store, "conversation_id", conversation_id)
    matched = waiting_runs_matching_event(waiting, event.type, agent_body)
    return matched[0] if matched else None
