from __future__ import annotations

from typing import Any

from domain.skill import FsmState, FsmTransition, SkillDefinition, SkillParam

DEFAULT_VERSION = "0.1.0"
VALID_PARAM_TYPES = frozenset({"string", "number", "boolean", "object", "array"})


def normalize_skill_param(raw: dict[str, Any]) -> SkillParam | None:
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    param_type = str(raw.get("type") or "string").strip() or "string"
    if param_type not in VALID_PARAM_TYPES:
        param_type = "string"
    return SkillParam(name=name, type=param_type, required=bool(raw.get("required")))


def skill_from_document(skill_doc: dict[str, Any]) -> SkillDefinition:
    states: list[FsmState] = []
    for state_doc in skill_doc.get("states", []):
        transitions = [
            FsmTransition(
                id=transition.get("id", ""),
                event=transition.get("event", ""),
                guard=transition.get("guard", ""),
                actions=list(transition.get("actions", [])),
                to=transition.get("to", ""),
            )
            for transition in state_doc.get("transitions", [])
        ]
        states.append(
            FsmState(
                id=state_doc["id"],
                on_enter=list(state_doc.get("onEnter", [])),
                final=bool(state_doc.get("final")),
                transitions=transitions,
            )
        )

    params = [
        param
        for raw in skill_doc.get("params", [])
        if isinstance(raw, dict)
        for param in [normalize_skill_param(raw)]
        if param is not None
    ]

    initial = skill_doc.get("initial") or (states[0].id if states else "")
    version = str(skill_doc.get("version") or DEFAULT_VERSION).strip() or DEFAULT_VERSION

    return SkillDefinition(
        id=skill_doc["id"],
        name=skill_doc.get("name", ""),
        description=skill_doc.get("description", ""),
        version=version,
        initial=initial,
        params=params,
        states=states,
    )
