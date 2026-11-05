from __future__ import annotations

from typing import Any

TALK_TO_AGENT = "talk_to_agent"
TALK_TO_HUMAN = "talk_to_human"
SYSTEM_ROLES = frozenset({TALK_TO_AGENT, TALK_TO_HUMAN})


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
    """A starter conversation skill. The FSM waits; it does not call tools yet."""
    if role == TALK_TO_AGENT:
        name = "Общение с агентом"
        description = (
            "Системный навык. Агент принимает сообщение от другого агента. "
            "В агентов проекта он входит сразу. Сообщения человека сюда не приходят."
        )
        event = "agent.message.received"
    elif role == TALK_TO_HUMAN:
        name = "Общение с человеком"
        description = (
            "Системный навык рантайма проекта. Человек говорит с проектом через этот навык. "
            "В агентов проекта он по умолчанию не входит."
        )
        event = "channel.message.received"
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
        "initial": "listening",
        "params": [{"name": "conversation_id", "type": "string", "required": False}],
        "states": [
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
        ],
        "viewport": {"panX": 0, "panY": 0, "zoom": 1},
        "flowDirection": "vertical",
    }


def library_agent_skills(now: str) -> list[dict[str, Any]]:
    return [system_skill(TALK_TO_AGENT, now=now)]


def runtime_agent_skills(now: str) -> list[dict[str, Any]]:
    return [
        system_skill(TALK_TO_AGENT, now=now),
        system_skill(TALK_TO_HUMAN, now=now),
    ]
