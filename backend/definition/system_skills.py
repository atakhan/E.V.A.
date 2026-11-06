from __future__ import annotations

from typing import Any

TALK_TO_AGENT = "talk_to_agent"
TALK_TO_HUMAN = "talk_to_human"
LIFE = "life"
SYSTEM_ROLES = frozenset({TALK_TO_AGENT, TALK_TO_HUMAN, LIFE})


def _state(state_id: str, name: str, *, y: float, transitions: list[dict[str, Any]] | None = None, final: bool = False) -> dict[str, Any]:
    return {
        "id": state_id,
        "name": name,
        "onEnter": [],
        "final": final,
        "transitions": transitions or [],
        "x": 80,
        "y": y,
        "width": 160,
        "height": 80,
    }


def system_skill(role: str, *, now: str) -> dict[str, Any]:
    """Platform skill shells. Life is the agent's global FSM; runtime executes it."""
    if role == TALK_TO_AGENT:
        name = "Общение с агентом"
        description = (
            "Системный навык. Агент принимает сообщение от другого агента. "
            "В агентов проекта он входит сразу. Сообщения человека сюда не приходят."
        )
        event = "agent.message.received"
        initial = "listening"
        states = [
            _state(
                "listening",
                "Слушает",
                y=40,
                transitions=[
                    {
                        "id": f"{role}_heard",
                        "event": event,
                        "guard": "",
                        "actions": [],
                        "to": "listening",
                    }
                ],
            )
        ]
        params: list[dict[str, Any]] = [{"name": "conversation_id", "type": "string", "required": False}]
    elif role == TALK_TO_HUMAN:
        name = "Общение с человеком"
        description = (
            "Системный навык рантайма проекта. Человек говорит с проектом через этот навык. "
            "В агентов проекта он по умолчанию не входит."
        )
        event = "channel.message.received"
        initial = "listening"
        states = [
            _state(
                "listening",
                "Слушает",
                y=40,
                transitions=[
                    {
                        "id": f"{role}_heard",
                        "event": event,
                        "guard": "",
                        "actions": [],
                        "to": "listening",
                    }
                ],
            )
        ]
        params = [{"name": "conversation_id", "type": "string", "required": False}]
    elif role == LIFE:
        # No channel/agent accepts on initial: life must not compete with talk_to_* for ingress.
        # Bootstrap event life.started keeps the thread in alive (waiting) after ensure_life_run.
        name = "Жизнь"
        description = (
            "Глобальный FSM агента — несущий процесс существования. "
            "Машина исполнения крутит эту нить; остальные навыки — эпизоды внутри жизни. "
            "Без навыка агент не жив."
        )
        initial = "alive"
        states = [
            _state(
                "alive",
                "Жив",
                y=40,
                transitions=[
                    {
                        "id": "life_started",
                        "event": "life.started",
                        "guard": "",
                        "actions": [],
                        "to": "alive",
                    }
                ],
            )
        ]
        params = []
    else:
        raise ValueError(f"Unknown system skill '{role}'")

    return {
        "id": role,
        "name": name,
        "description": description,
        "version": "0.1.0",
        "createdAt": now,
        "updatedAt": now,
        "systemRole": role,
        "initial": initial,
        "params": params,
        "states": states,
        "viewport": {"panX": 0, "panY": 0, "zoom": 1},
        "flowDirection": "vertical",
    }


def library_agent_skills(now: str) -> list[dict[str, Any]]:
    return [
        system_skill(TALK_TO_AGENT, now=now),
        system_skill(LIFE, now=now),
    ]


def runtime_agent_skills(now: str) -> list[dict[str, Any]]:
    return [
        system_skill(TALK_TO_AGENT, now=now),
        system_skill(TALK_TO_HUMAN, now=now),
        system_skill(LIFE, now=now),
    ]


def ensure_life_skill_in_body(body: dict[str, Any], *, now: str) -> bool:
    """Append empty «Жизнь» if missing. Returns True when the draft changed."""
    skills = [item for item in (body.get("skills") or []) if isinstance(item, dict)]
    if any(item.get("id") == LIFE or item.get("systemRole") == LIFE for item in skills):
        return False
    skills.append(system_skill(LIFE, now=now))
    body["skills"] = skills
    return True
