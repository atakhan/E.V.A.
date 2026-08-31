from __future__ import annotations

import re
from typing import Any

_GUARD_RE = re.compile(
    r"^(?P<left>[\w.]+)\s*(?P<op>==|!=|>=|<=|>|<)\s*(?P<right>.+)$"
)


def _resolve_path(root: dict[str, Any], path: str) -> Any:
    cur: Any = root
    for part in path.split("."):
        if part == "length":
            if isinstance(cur, (list, str, dict)):
                return len(cur)
            return None
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _parse_literal(raw: str) -> Any:
    value = raw.strip()
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "None"):
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def build_guard_scope(
    *,
    vars: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        result = {}
    return {
        "vars": vars,
        "payload": payload,
        "event": payload,
        "result": result,
        "needs_clarification": vars.get("needs_clarification"),
    }


def is_valid_guard_syntax(guard: str) -> bool:
    expression = (guard or "").strip()
    if not expression:
        return True
    return bool(_GUARD_RE.match(expression))


def evaluate_guard(guard: str, *, vars: dict[str, Any], payload: dict[str, Any]) -> bool:
    """Safe guards: empty = true; comparisons on paths in vars/payload/result/event."""
    expression = (guard or "").strip()
    if not expression:
        return True

    match = _GUARD_RE.match(expression)
    if not match:
        return False

    scope = build_guard_scope(vars=vars, payload=payload)
    left_raw = match.group("left")
    right_raw = match.group("right").strip()
    op = match.group("op")

    left = _resolve_path(scope, left_raw) if "." in left_raw else scope.get(left_raw)
    if right_raw.startswith(("vars.", "payload.", "result.", "event.")):
        right = _resolve_path(scope, right_raw)
    else:
        right = _parse_literal(right_raw)

    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if left is None or right is None:
        return False
    try:
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
    except TypeError:
        return False
    return False
