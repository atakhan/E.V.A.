from __future__ import annotations

from typing import Any


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
