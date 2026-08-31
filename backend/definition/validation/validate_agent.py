from __future__ import annotations

import re
from typing import Any, Literal

from definition.catalog.builtin_tools import get_tool_definition
from definition.validation.validate_skill import validate_skill
from runtime.tool_instance_resolver import list_tool_instances, resolve_recipe_tool

AgentIssueSeverity = Literal["error", "warning", "info"]
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_VALID_POLICIES = frozenset({"auto", "needs_human"})
_CREDENTIAL_TYPES = frozenset({"telegram", "polza_ai_llm", "web_client"})


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
    instances = list_tool_instances(agent)
    enabled_instance_ids = {item["id"] for item in instances if item.get("enabled")}
    referenced_actions = _collect_referenced_action_ids(agent)
    slug = agent.get("slug", "")
    tools_href = f"/agents/{slug}/tools" if slug else None
    actions_href = f"/agents/{slug}/actions" if slug else None

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
        skill_href = f"/agents/{slug}/skills/{skill_id}" if slug else None
        issues.extend(validate_skill(skill, action_ids=action_ids, href=skill_href))

    for action in agent.get("actions", []):
        action_id = action.get("id", "")
        action_name = action.get("name", action_id)
        recipe = action.get("recipe", [])
        version = str(action.get("version") or "0.1.0")
        policy = str(action.get("policy") or "auto")

        if not _SEMVER_RE.match(version):
            issues.append(
                _issue(
                    f"action.{action_id}.bad-version",
                    "warning",
                    "invalid_action_version",
                    f"Action «{action_name}»: version «{version}» не SemVer (ожидается X.Y.Z)",
                    actions_href,
                )
            )

        if policy not in _VALID_POLICIES:
            issues.append(
                _issue(
                    f"action.{action_id}.bad-policy",
                    "error",
                    "invalid_action_policy",
                    f"Action «{action_name}»: policy «{policy}» недопустим",
                    actions_href,
                )
            )

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

        step_ids: set[str] = set()
        for step in recipe:
            step_id = step.get("id", "")
            if step_id:
                if step_id in step_ids:
                    issues.append(
                        _issue(
                            f"action.{action_id}.step.{step_id}.duplicate",
                            "error",
                            "duplicate_step_id",
                            f"Action «{action_name}»: дублирующийся step id «{step_id}»",
                            actions_href,
                        )
                    )
                step_ids.add(step_id)

            tool_ref = step.get("tool", "")
            command = step.get("command", "")
            resolved = resolve_recipe_tool(agent, tool_ref) if tool_ref else None
            type_id = resolved.type_id if resolved else tool_ref
            label = f"{tool_ref}.{command}" if tool_ref and command else tool_ref or command or "шаг"
            tool_def = get_tool_definition(type_id) if type_id else None

            if not tool_ref or resolved is None:
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.unknown-tool",
                        "error",
                        "unknown_tool_instance",
                        f"Action «{action_name}»: неизвестный Tool instance в шаге «{label}»",
                        actions_href,
                    )
                )
                continue

            if resolved.status == "ambiguous":
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.ambiguous-tool",
                        "error",
                        "ambiguous_tool_reference",
                        f"Action «{action_name}»: «{tool_ref}» неоднозначен — укажите конкретный instance id",
                        actions_href,
                    )
                )
                continue

            if resolved.status == "disabled":
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.tool-off",
                        "error",
                        "disabled_tool_instance",
                        f"Action «{action_name}»: instance «{resolved.instance_id}» выключен",
                        tools_href,
                    )
                )
            elif resolved.instance_id not in enabled_instance_ids:
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.tool-off",
                        "error",
                        "disabled_tool_instance",
                        f"Action «{action_name}»: instance «{resolved.instance_id}» не подключён",
                        tools_href,
                    )
                )

            if not tool_def:
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.unknown-type",
                        "error",
                        "unknown_tool",
                        f"Action «{action_name}»: неизвестный тип Tool «{type_id}»",
                        actions_href,
                    )
                )
                continue

            if command and not any(cmd["id"] == command for cmd in tool_def.get("commands", [])):
                issues.append(
                    _issue(
                        f"action.{action_id}.step.{step_id}.unknown-command",
                        "error",
                        "unknown_command",
                        f"Action «{action_name}»: нет команды «{type_id}.{command}» в каталоге",
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
    if not enabled_instance_ids and has_recipe:
        issues.append(
            _issue(
                "agent.no-enabled-tools",
                "warning",
                "no_enabled_tools",
                "Есть Actions с recipe, но ни один Tool instance не подключён",
                tools_href,
            )
        )

    telegram_creds_seen: set[str] = set()
    for item in instances:
        if not item.get("enabled"):
            continue
        tool_type = item.get("toolId", "")
        instance_id = item.get("id", "")
        if tool_type in _CREDENTIAL_TYPES and not item.get("credentialId"):
            label = {"telegram": "Telegram", "polza_ai_llm": "PolzaAI_LLM", "web_client": "Web Client"}.get(
                tool_type, tool_type
            )
            issues.append(
                _issue(
                    f"tool.{instance_id}.missing-credential",
                    "error",
                    "missing_credential",
                    f"{label} instance «{item.get('name', instance_id)}» без credential",
                    tools_href,
                )
            )
        if tool_type == "telegram" and item.get("credentialId"):
            cred = str(item["credentialId"])
            if cred in telegram_creds_seen:
                issues.append(
                    _issue(
                        f"tool.{instance_id}.duplicate-credential",
                        "error",
                        "duplicate_credential",
                        "Telegram instances не могут использовать один credential",
                        tools_href,
                    )
                )
            telegram_creds_seen.add(cred)

    errors = sum(1 for issue in issues if issue["severity"] == "error")
    warnings = sum(1 for issue in issues if issue["severity"] == "warning")
    infos = sum(1 for issue in issues if issue["severity"] == "info")
    return {"issues": issues, "errors": errors, "warnings": warnings, "infos": infos}
