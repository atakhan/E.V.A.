from __future__ import annotations

from typing import Any

from definition.behavior.graph import normalize_guard


def fsm_behaviorally_equivalent(
    left_states: list[dict[str, Any]] | None,
    left_initial: str | None,
    right_states: list[dict[str, Any]] | None,
    right_initial: str | None,
) -> bool:
    """Bisimulation on (event, normalized guard, actions). Ignores state ids and origin metadata."""
    left_states = list(left_states or [])
    right_states = list(right_states or [])
    if not left_states and not right_states:
        return True
    left_index = {str(state["id"]): state for state in left_states if state.get("id")}
    right_index = {str(state["id"]): state for state in right_states if state.get("id")}
    if not left_initial or left_initial not in left_index:
        return False
    if not right_initial or right_initial not in right_index:
        return False

    mapping: dict[str, str] = {}

    def labels(state: dict[str, Any]) -> list[tuple[str, str, tuple[str, ...], str]]:
        rows: list[tuple[str, str, tuple[str, ...], str]] = []
        for transition in state.get("transitions") or []:
            rows.append(
                (
                    str(transition.get("event") or ""),
                    normalize_guard(transition.get("guard")),
                    tuple(str(action) for action in (transition.get("actions") or []) if action),
                    str(transition.get("to") or ""),
                )
            )
        return sorted(rows)

    def match(left_id: str, right_id: str, stack: set[tuple[str, str]]) -> bool:
        if (left_id, right_id) in stack:
            return True
        if left_id in mapping:
            return mapping[left_id] == right_id
        left_state = left_index.get(left_id)
        right_state = right_index.get(right_id)
        if left_state is None or right_state is None:
            return False
        left_rows = labels(left_state)
        right_rows = labels(right_state)
        if [row[:3] for row in left_rows] != [row[:3] for row in right_rows]:
            return False
        if bool(left_state.get("final")) != bool(right_state.get("final")):
            # final with outgoing still comparable by transitions; only compare final when no trans mismatch
            if not left_rows and not right_rows:
                return bool(left_state.get("final")) == bool(right_state.get("final"))
        mapping[left_id] = right_id
        stack.add((left_id, right_id))
        for left_row, right_row in zip(left_rows, right_rows, strict=True):
            if not match(left_row[3], right_row[3], stack):
                return False
        return True

    return match(left_initial, right_initial, set())
