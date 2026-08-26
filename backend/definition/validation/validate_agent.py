from __future__ import annotations

from typing import Any, Literal

from definition.catalog.builtin_tools import get_tool_definition

AgentIssueSeverity = Literal["error", "warning", "info"]


def _issue(
    issue_id: str,
    severity: AgentIssueSeverity,
    code: str,
    message: str,
    href: str | None = None,
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "severity": severity,
        "code": code,
        "message": message,
        "href": href,
    }


def _collect_referenced_action_ids(agent: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for skill in agent.get("skills", []):
        for state in skill.get("states", []):
            for action_id in state.get("onEnter", []):
                ids.add(action_id)
            for transition in state.get("transitions", []):
                for action_id in transition.get("actions", []):
                    ids.add(action_id)
    return ids


def validate_agent(agent: dict[str, Any]) -> dict[str, Any]:
    """Port of frontend validateAgent.ts — operates on camelCase agent dict."""
    issues: list[dict[str, Any]] = []
    action_ids = {action["id"] for action in agent.get("actions", []) if action.get("id")}
    enabled_tools = {
        tool["toolId"]
        for tool in agent.get("tools", [])
        if tool.get("enabled") and tool.get("toolId")
    }
    referenced_actions = _collect_referenced_action_ids(agent)
    slug = agent.get("slug", "")

    if not agent.get("skills"):
        issues.append(
            _issue(
                "agent.no-skills",
                "info",
                "no_skills",
                "У агента пока нет Skills",
                f"/agents/{slug}/skills" if slug else None,
            )
        )

    for skill in agent.get("skills", []):
        skill_id = skill.get("id", "")
        skill_name = skill.get("name", skill_id)
        skill_href = f"/agents/{slug}/skills/{skill_id}" if slug else None
        state_ids = {state["id"] for state in skill.get("states", []) if state.get("id")}

        if not skill.get("states"):
            issues.append(
                _issue(
                    f"skill.{skill_id}.empty",
                    "warning",
                    "skill_empty",
                    f"Skill «{skill_name}» без states",
                    skill_href,
                )
            )
            continue

        initial = skill.get("initial")
        if not initial:
            issues.append(
                _issue(
                    f"skill.{skill_id}.no-initial",
                    "error",
                    "missing_initial",
                    f"Skill «{skill_name}»: не задан initial state",
                    skill_href,
                )
            )
        elif initial not in state_ids:
            issues.append(
                _issue(
                    f"skill.{skill_id}.bad-initial",
                    "error",
                    "invalid_initial",
                    f"Skill «{skill_name}»: initial «{initial}» отсутствует среди states",
                    skill_href,
                )
            )

        for state in skill.get("states", []):
            state_id = state.get("id", "")
            for action_id in state.get("onEnter", []):
                if action_id not in action_ids:
                    issues.append(
                        _issue(
                            f"skill.{skill_id}.state.{state_id}.on_enter.{action_id}",
                            "error",
                            "unknown_action",
                            f"Skill «{skill_name}» / {state_id}: on_enter ссылается на неизвестный Action «{action_id}»",
                            skill_href,
                        )
                    )

            for transition in state.get("transitions", []):
                transition_id = transition.get("id", "")
                event = (transition.get("event") or "").strip()
                if not event:
                    issues.append(
                        _issue(
                            f"skill.{skill_id}.transition.{transition_id}.event",
                            "warning",
                            "empty_event",
                            f"Skill «{skill_name}» / {state_id}→{transition.get('to') or '?'}: пустой event",
                            skill_href,
                        )
                    )

                to_state = transition.get("to")
                if not to_state or to_state not in state_ids:
                    issues.append(
                        _issue(
                            f"skill.{skill_id}.transition.{transition_id}.to",
                            "error",
                            "invalid_transition_target",
                            f"Skill «{skill_name}» / {state_id}: переход ведёт в неизвестный state «{to_state or '—'}»",
                            skill_href,
                        )
                    )

                for action_id in transition.get("actions", []):
                    if action_id not in action_ids:
                        issues.append(
                            _issue(
                                f"skill.{skill_id}.transition.{transition_id}.action.{action_id}",
                                "error",
                                "unknown_action",
                                f"Skill «{skill_name}» / {state_id}: transition ссылается на неизвестный Action «{action_id}»",
                                skill_href,
                            )
                        )

    actions_href = f"/agents/{slug}/actions" if slug else None
    tools_href = f"/agents/{slug}/tools" if slug else None

    for action in agent.get("actions", []):
        action_id = action.get("id", "")
        action_name = action.get("name", action_id)
        recipe = action.get("recipe", [])

        if not recipe:
            issues.append(
                _issue(
                    f"action.{action_id}.empty-recipe",
                    "warning",
                    "empty_recipe",
                    f"Action «{action_name}» без шагов recipe",
                    actions_href,
                )
            )

        for step in recipe:
            step_id = step.get("id", "")
            tool_id = step.get("tool", "")
            command = step.get("command", "")
            label = f"{tool_id}.{command}" if tool_id and command else tool_id or command or "шаг"
            tool_def = get_tool_definition(tool_id) if tool_id else None

            if not tool_id or not tool_def:
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.unknown-tool",
                        "error",
                        "unknown_tool",
                        f"Action «{action_name}»: неизвестный Tool в шаге «{label}»",
                        actions_href,
                    )
                )
                continue

            if tool_id not in enabled_tools:
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.tool-off",
                        "error",
                        "disabled_tool",
                        f"Action «{action_name}»: Tool «{tool_id}» не подключён у агента",
                        tools_href,
                    )
                )

            if command and not any(cmd["id"] == command for cmd in tool_def.get("commands", [])):
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.unknown-command",
                        "error",
                        "unknown_command",
                        f"Action «{action_name}»: нет команды «{tool_id}.{command}» в каталоге",
                        actions_href,
                    )
                )

        if action_id not in referenced_actions:
            issues.append(
                _issue(
                    f"action.{action_id}.unused",
                    "info",
                    "unused_action",
                    f"Action «{action_name}» нигде не используется в Skills",
                    actions_href,
                )
            )

    has_recipe = any(action.get("recipe") for action in agent.get("actions", []))
    if not enabled_tools and has_recipe:
        issues.append(
            _issue(
                "agent.no-enabled-tools",
                "warning",
                "no_enabled_tools",
                "Есть Actions с recipe, но ни один Tool не подключён",
                tools_href,
            )
        )

    for tool in agent.get("tools", []):
        if not tool.get("enabled"):
            continue
        tool_id = tool.get("toolId", "")
        if tool_id == "telegram" and not tool.get("credentialId"):
            issues.append(
                _issue(
                    f"tool.{tool_id}.missing-credential",
                    "error",
                    "missing_credential",
                    "Telegram подключён, но не выбран credential (bot token)",
                    tools_href,
                )
            )

    errors = sum(1 for issue in issues if issue["severity"] == "error")
    warnings = sum(1 for issue in issues if issue["severity"] == "warning")
    infos = sum(1 for issue in issues if issue["severity"] == "info")
    return {"issues": issues, "errors": errors, "warnings": warnings, "infos": infos}
