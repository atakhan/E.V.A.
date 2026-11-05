from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RECEIVED = "agent.message.received"
DECLINED = "agent.message.declined"

UNKNOWN = "не принимаю"
AMBIGUOUS = "неоднозначно"
NO_ANSWER = "не отвечает"
NO_REPLY = "ответ не разрешён"
NO_CONNECTOR = "нет коннектора"
NOT_PUBLISHED = "агент не опубликован"
NOT_LISTENING = "навык не слушает"
NO_MATTER = "не указано дело"
NO_PROJECT = "агент не в проекте"
NOT_HERE = "нет такого агента"


@dataclass(frozen=True)
class Decision:
    deliver: bool
    reason: str = ""
    skill_id: str | None = None
    reply_allowed: bool = False


def _initial_id(skill: dict[str, Any]) -> str | None:
    initial = skill.get("initial")
    if isinstance(initial, str) and initial:
        return initial
    states = skill.get("states") or []
    if states and isinstance(states[0], dict):
        state_id = states[0].get("id")
        return str(state_id) if state_id else None
    return None


def listens_for_agent_message(skill: dict[str, Any]) -> bool:
    initial = _initial_id(skill)
    if not initial:
        return False
    for state in skill.get("states") or []:
        if not isinstance(state, dict) or state.get("id") != initial:
            continue
        for transition in state.get("transitions") or []:
            if isinstance(transition, dict) and transition.get("event") == RECEIVED:
                return True
    return False


def judge(skills: list[dict[str, Any]], matter: str, waits: bool) -> Decision:
    """Match one skill that accepts `matter` and decide whether a reply may be waited for."""
    name = matter.strip()
    if not name:
        return Decision(False, NO_MATTER)
    matched = [
        skill
        for skill in skills
        if isinstance(skill, dict) and str(skill.get("accepts") or "").strip() == name
    ]
    if not matched:
        return Decision(False, UNKNOWN)
    if len(matched) > 1:
        return Decision(False, AMBIGUOUS)
    skill = matched[0]
    answers = skill.get("answers") is True
    if waits and not answers:
        return Decision(False, NO_ANSWER)
    if not listens_for_agent_message(skill):
        return Decision(False, NOT_LISTENING)
    return Decision(
        True,
        skill_id=str(skill.get("id") or ""),
        reply_allowed=waits and answers,
    )
