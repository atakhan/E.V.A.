from __future__ import annotations

import re
from typing import Any

_EQ_RE = re.compile(
    r"^(?P<left>[\w.]+)\s*(?P<op>==|!=)\s*(?P<right>.+)$"
)


def _resolve_path(root: dict[str, Any], path: str) -> Any:
    cur: Any = root
    for part in path.split("."):
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


def evaluate_guard(guard: str, *, vars: dict[str, Any], payload: dict[str, Any]) -> bool:
    """Minimal safe guards: empty = true; field equality against literals or paths."""
    expression = (guard or "").strip()
    if not expression:
        return True

    match = _EQ_RE.match(expression)
    if not match:
        return False

    scope = {"vars": vars, "payload": payload, "needs_clarification": vars.get("needs_clarification")}
    left_raw = match.group("left")
    right_raw = match.group("right").strip()
    op = match.group("op")

    left = _resolve_path(scope, left_raw) if "." in left_raw else scope.get(left_raw)
    if right_raw.startswith(("vars.", "payload.")):
        right = _resolve_path(scope, right_raw)
    else:
        right = _parse_literal(right_raw)

    if op == "==":
        return left == right
    return left != right
