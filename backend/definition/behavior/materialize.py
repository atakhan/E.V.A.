from __future__ import annotations

from typing import Any

from definition.behavior.compile import compile_behavior


_BEHAVIOR_FIELDS = ("behavior", "execution", "storyViewport", "logicViewport")


def skill_has_behavior(skill: dict[str, Any]) -> bool:
    behavior = skill.get("behavior")
    if not isinstance(behavior, dict):
        return False
    return bool(behavior.get("nodes"))


def strip_behavior_fields(skill: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in skill.items() if key not in _BEHAVIOR_FIELDS}


def flatten_skill_document(
    skill: dict[str, Any],
    *,
    action_ids: set[str] | None = None,
) -> dict[str, Any]:
    """One-shot: leftover Behavior Graph → FSM states[], then drop the graph."""
    next_skill = dict(skill)
    if skill_has_behavior(next_skill):
        result = compile_behavior(next_skill["behavior"], action_ids=action_ids)
        if result["ok"] and result["artifact"] is not None:
            artifact = result["artifact"]
            next_skill["initial"] = artifact["initial"]
            next_skill["states"] = artifact["states"]
    return strip_behavior_fields(next_skill)


def flatten_agent_document(agent: dict[str, Any]) -> dict[str, Any]:
    action_ids = {str(action["id"]) for action in agent.get("actions") or [] if action.get("id")}
    skills = [
        flatten_skill_document(skill, action_ids=action_ids) for skill in agent.get("skills") or []
    ]
    return {**agent, "skills": skills}
