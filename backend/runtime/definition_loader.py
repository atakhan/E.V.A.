from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from domain.action import ActionDefinition, ActionRecipeStep
from domain.skill import FsmState, FsmTransition, SkillDefinition
from runtime.event_router import RuntimeCatalog
from tools.credential_resolver import get_telegram_token_for_binding
from tools.llm_stub import LlmStubTool
from tools.registry import ToolRegistry
from tools.telegram_stub import TelegramStubTool
from tools.telegram_tool import TelegramTool


def parse_action_args(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    text = str(raw).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        return {"raw": text}


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

    initial = skill_doc.get("initial") or (states[0].id if states else "")
    return SkillDefinition(
        id=skill_doc["id"],
        name=skill_doc.get("name", ""),
        description=skill_doc.get("description", ""),
        version=skill_doc.get("version", "0.1.0"),
        initial=initial,
        states=states,
    )


def actions_from_document(actions_doc: list[dict[str, Any]]) -> dict[str, ActionDefinition]:
    actions: dict[str, ActionDefinition] = {}
    for action_doc in actions_doc:
        recipe = [
            ActionRecipeStep(
                id=step.get("id", ""),
                tool=step.get("tool", ""),
                command=step.get("command", ""),
                args=parse_action_args(step.get("args")),
            )
            for step in action_doc.get("recipe", [])
        ]
        actions[action_doc["id"]] = ActionDefinition(
            id=action_doc["id"],
            name=action_doc.get("name", ""),
            description=action_doc.get("description", ""),
            recipe=recipe,
        )
    return actions


def build_tool_registry(
    agent_body: dict[str, Any],
    *,
    agent_id: str,
    session,
) -> ToolRegistry:
    settings = get_settings()
    enabled_bindings = [
        binding
        for binding in agent_body.get("tools", [])
        if binding.get("enabled") and binding.get("toolId")
    ]
    enabled = {binding["toolId"] for binding in enabled_bindings}

    tools = []
    if "llm" in enabled:
        tools.append(LlmStubTool())

    if "telegram" in enabled:
        binding = next(b for b in enabled_bindings if b["toolId"] == "telegram")
        if settings.telegram_mode == "stub":
            tools.append(TelegramStubTool())
        else:
            token = get_telegram_token_for_binding(session, agent_id, binding)
            if not token:
                raise KeyError("Telegram enabled but credential bot_token not found")
            tools.append(TelegramTool(token))

    return ToolRegistry(tools)


def load_runtime_catalog(agent_body: dict[str, Any], skill_id: str) -> RuntimeCatalog:
    skill_doc = next((skill for skill in agent_body.get("skills", []) if skill.get("id") == skill_id), None)
    if skill_doc is None:
        raise KeyError(f"Skill '{skill_id}' not found in agent document")

    skill = skill_from_document(skill_doc)
    actions = actions_from_document(agent_body.get("actions", []))
    return RuntimeCatalog(skill=skill, actions=actions)
