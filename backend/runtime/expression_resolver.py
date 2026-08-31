from __future__ import annotations

import re
from typing import Any

_TEMPLATE_RE = re.compile(r"\{\{([^}]+)\}\}")
_LEGACY_VAR_RE = re.compile(r"\$\{vars\.([a-zA-Z0-9_]+)\}")


def _resolve_path(root: dict[str, Any], path: str) -> Any:
    cur: Any = root
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _resolve_template_string(template: str, scope: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        value = _resolve_path(scope, path) if "." in path else scope.get(path)
        return "" if value is None else str(value)

    resolved = _TEMPLATE_RE.sub(repl, template)

    def legacy(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(scope.get("vars", {}).get(key, ""))

    return _LEGACY_VAR_RE.sub(legacy, resolved)


def resolve_value(value: Any, scope: dict[str, Any]) -> Any:
    if isinstance(value, str):
        if "{{" in value or "${vars." in value:
            return _resolve_template_string(value, scope)
        return value
    if isinstance(value, dict):
        return {key: resolve_value(item, scope) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_value(item, scope) for item in value]
    return value


def build_action_input(vars: dict[str, Any]) -> dict[str, Any]:
    text = vars.get("last_message") or vars.get("text")
    payload = {
        "request_id": vars.get("request_id"),
        "message": text,
        "message_id": vars.get("message_id"),
        "conversation_id": vars.get("conversation_id"),
    }
    for key, value in vars.items():
        if key.startswith("_"):
            continue
        if key not in payload:
            payload[key] = value
    return payload
