from __future__ import annotations

import re
from typing import Any, Literal

from runtime.guards import is_valid_guard_syntax
from definition.behavior.compile import compile_behavior
from definition.behavior.validate import validate_behavior_graph

AgentIssueSeverity = Literal["error", "warning", "info"]
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


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


def _reachable_states(skill: dict[str, Any]) -> set[str]:
    states = skill.get("states", [])
    state_ids = {state["id"] for state in states if state.get("id")}
    initial = skill.get("initial")
    if not initial or initial not in state_ids:
        return set()

    reachable: set[str] = {initial}
    queue = [initial]
    while queue:
        current = queue.pop(0)
        state = next((item for item in states if item.get("id") == current), None)
        if state is None:
            continue
        for transition in state.get("transitions", []):
            target = transition.get("to")
            if target in state_ids and target not in reachable:
                reachable.add(target)
                queue.append(target)
    return reachable


def validate_skill(
    skill: dict[str, Any],
    *,
    action_ids: set[str],
    href: str | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    skill_id = skill.get("id", "")
    skill_name = skill.get("name", skill_id)
    version = str(skill.get("version") or "0.1.0")

    if not _SEMVER_RE.match(version):
        issues.append(
            _issue(
                f"skill.{skill_id}.bad-version",
                "warning",
                "invalid_skill_version",
                f"Skill «{skill_name}»: version «{version}» не SemVer (ожидается X.Y.Z)",
                href,
            )
        )

    behavior = skill.get("behavior") if isinstance(skill.get("behavior"), dict) else None
    has_behavior = bool(behavior and behavior.get("nodes"))
    if has_behavior:
        for issue in validate_behavior_graph(behavior, action_ids=action_ids, skill_id=skill_id):
            issues.append(
                _issue(
                    f"skill.{skill_id}.behavior.{issue.get('code')}.{issue.get('nodeId') or 'graph'}",
                    issue.get("severity") or "error",
                    str(issue.get("code") or "behavior"),
                    f"Skill «{skill_name}»: {issue.get('message')}",
                    href,
                )
            )
        compiled = compile_behavior(behavior, action_ids=action_ids)
        if compiled["ok"] and compiled["artifact"]:
            skill = {
                **skill,
                "states": compiled["artifact"]["states"],
                "initial": compiled["artifact"]["initial"],
            }

    state_ids = {state["id"] for state in skill.get("states", []) if state.get("id")}

    if not skill.get("states"):
        issues.append(
            _issue(
                f"skill.{skill_id}.empty",
                "warning",
                "skill_empty",
                f"Skill «{skill_name}» без states",
                href,
            )
        )
        return issues

    initial = skill.get("initial")
    if not initial:
        issues.append(
            _issue(
                f"skill.{skill_id}.no-initial",
                "error",
                "missing_initial",
                f"Skill «{skill_name}»: не задан initial state",
                href,
            )
        )
    elif initial not in state_ids:
        issues.append(
            _issue(
                f"skill.{skill_id}.bad-initial",
                "error",
                "invalid_initial",
                f"Skill «{skill_name}»: initial «{initial}» отсутствует среди states",
                href,
            )
        )

    reachable = _reachable_states(skill)
    for state in skill.get("states", []):
        state_id = state.get("id", "")
        if state_id and state_id not in reachable and state_id != initial:
            issues.append(
                _issue(
                    f"skill.{skill_id}.state.{state_id}.unreachable",
                    "warning",
                    "unreachable_state",
                    f"Skill «{skill_name}» / {state_id}: state недостижим из initial",
                    href,
                )
            )

        if not state.get("final"):
            has_outgoing = bool(state.get("transitions")) or bool(state.get("onEnter"))
            if not has_outgoing and state_id in reachable:
                issues.append(
                    _issue(
                        f"skill.{skill_id}.state.{state_id}.dead-end",
                        "warning",
                        "dead_end_state",
                        f"Skill «{skill_name}» / {state_id}: не-final state без переходов",
                        href,
                    )
                )

        for action_id in state.get("onEnter", []):
            if action_id not in action_ids:
                issues.append(
                    _issue(
                        f"skill.{skill_id}.state.{state_id}.on_enter.{action_id}",
                        "error",
                        "unknown_action",
                        f"Skill «{skill_name}» / {state_id}: on_enter ссылается на неизвестный Action «{action_id}»",
                        href,
                    )
                )

        events_seen: dict[str, list[str]] = {}
        for transition in state.get("transitions", []):
            transition_id = transition.get("id", "")
            event = (transition.get("event") or "").strip()
            guard = transition.get("guard", "")

            if not event:
                issues.append(
                    _issue(
                        f"skill.{skill_id}.transition.{transition_id}.event",
                        "warning",
                        "empty_event",
                        f"Skill «{skill_name}» / {state_id}→{transition.get('to') or '?'}: пустой event",
                        href,
                    )
                )

            if guard and not is_valid_guard_syntax(guard):
                issues.append(
                    _issue(
                        f"skill.{skill_id}.transition.{transition_id}.guard",
                        "error",
                        "invalid_guard_syntax",
                        f"Skill «{skill_name}» / {state_id}: guard «{guard}» синтаксически невалиден",
                        href,
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
                        href,
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
                            href,
                        )
                    )

            if event:
                key = f"{state_id}:{event}"
                events_seen.setdefault(key, []).append(guard.strip() or "")

        for key, guards in events_seen.items():
            empty_guards = [item for item in guards if not item]
            if len(empty_guards) > 1:
                _, event_name = key.split(":", 1)
                issues.append(
                    _issue(
                        f"skill.{skill_id}.state.{state_id}.event.{event_name}.ambiguous",
                        "warning",
                        "ambiguous_guards",
                        f"Skill «{skill_name}» / {state_id}: event «{event_name}» имеет несколько handlers без guard",
                        href,
                    )
                )

    for param in skill.get("params", []):
        name = str(param.get("name") or "").strip()
        if not name:
            issues.append(
                _issue(
                    f"skill.{skill_id}.param.empty",
                    "warning",
                    "empty_param_name",
                    f"Skill «{skill_name}»: param без name",
                    href,
                )
            )

    return issues
