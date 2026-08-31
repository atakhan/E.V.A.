from __future__ import annotations

import json
from typing import Any

from domain.action import ActionDefinition, ActionRecipeStep

DEFAULT_VERSION = "0.1.0"
DEFAULT_POLICY = "auto"
VALID_POLICIES = frozenset({"auto", "needs_human"})


def _parse_json_object(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def normalize_recipe_step(raw: dict[str, Any], *, fallback_id: str) -> ActionRecipeStep:
    step_id = str(raw.get("id") or fallback_id).strip() or fallback_id
    tool = str(raw.get("tool") or "").strip()
    command = str(raw.get("command") or "").strip()
    when = str(raw.get("when") or "").strip()

    input_data = raw.get("input")
    if input_data is None:
        input_data = _parse_json_object(raw.get("args"))

    return ActionRecipeStep(
        id=step_id,
        tool=tool,
        command=command,
        input=input_data,
        when=when,
    )


def normalize_action_document(raw: dict[str, Any]) -> ActionDefinition:
    action_id = str(raw.get("id") or "").strip()
    version = str(raw.get("version") or DEFAULT_VERSION).strip() or DEFAULT_VERSION
    policy = str(raw.get("policy") or DEFAULT_POLICY).strip() or DEFAULT_POLICY
    if policy not in VALID_POLICIES:
        policy = DEFAULT_POLICY

    recipe_raw = raw.get("recipe") if isinstance(raw.get("recipe"), list) else []
    recipe = [
        normalize_recipe_step(step if isinstance(step, dict) else {}, fallback_id=f"step_{index + 1}")
        for index, step in enumerate(recipe_raw)
    ]

    on_failure = str(raw.get("onFailure") or raw.get("on_failure") or "").strip()
    if not on_failure and policy == "needs_human":
        on_failure = "needs_human"
    if on_failure not in ("fail", "needs_human", "retry"):
        on_failure = "fail" if policy != "needs_human" else "needs_human"

    retry_raw = raw.get("retry")
    retry = retry_raw if isinstance(retry_raw, dict) else {}
    timeout_ms = raw.get("timeoutMs") or raw.get("timeout_ms")
    timeout_value = int(timeout_ms) if timeout_ms is not None else None

    return ActionDefinition(
        id=action_id,
        name=str(raw.get("name") or action_id),
        description=str(raw.get("description") or ""),
        version=version,
        policy=policy,
        on_failure=on_failure,
        retry=retry,
        timeout_ms=timeout_value,
        input_schema=_parse_json_object(raw.get("inputSchema") or raw.get("input_schema")),
        output_schema=_parse_json_object(raw.get("outputSchema") or raw.get("output_schema")),
        recipe=recipe,
    )
