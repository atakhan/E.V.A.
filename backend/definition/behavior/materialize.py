from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from definition.behavior.compile import compile_behavior
from definition.behavior.lift import lift_fsm_to_behavior


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def skill_has_behavior(skill: dict[str, Any]) -> bool:
    behavior = skill.get("behavior")
    if not isinstance(behavior, dict):
        return False
    return bool(behavior.get("nodes"))


def ensure_behavior(skill: dict[str, Any]) -> dict[str, Any]:
    if skill_has_behavior(skill):
        return skill
    states = skill.get("states") or []
    if not states:
        return skill
    lifted = lift_fsm_to_behavior(states, skill.get("initial"))
    return {**skill, "behavior": lifted}


def materialize_skill_execution(
    skill: dict[str, Any],
    *,
    action_ids: set[str] | None = None,
    compiled_at: str | None = None,
) -> dict[str, Any]:
    """On publish: compile behavior into execution artifact and flat states[]."""
    if not skill_has_behavior(skill):
        return {"ok": True, "skill": skill, "errors": []}

    stamp = compiled_at or _utcnow_iso()
    result = compile_behavior(skill["behavior"], compiled_at=stamp, action_ids=action_ids)
    if not result["ok"] or result["artifact"] is None:
        return {"ok": False, "skill": skill, "errors": result["errors"]}

    artifact = result["artifact"]
    next_skill = {
        **skill,
        "initial": artifact["initial"],
        "states": artifact["states"],
        "execution": artifact,
    }
    return {"ok": True, "skill": next_skill, "errors": result["errors"]}


def materialize_agent_for_publish(agent: dict[str, Any]) -> dict[str, Any]:
    action_ids = {str(action["id"]) for action in agent.get("actions") or [] if action.get("id")}
    skills: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for skill in agent.get("skills") or []:
        result = materialize_skill_execution(skill, action_ids=action_ids)
        skills.append(result["skill"])
        if not result["ok"]:
            skill_id = skill.get("id") or ""
            for issue in result["errors"]:
                errors.append({**issue, "skillId": skill_id})
    return {"ok": not errors, "agent": {**agent, "skills": skills}, "errors": errors}
