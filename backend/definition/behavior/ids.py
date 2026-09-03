from __future__ import annotations

import re

COMPILER_VERSION = "1"
GRAPH_VERSION = 1

_SANITIZE = re.compile(r"[^A-Za-z0-9_]+")


def sanitize_id(raw: str) -> str:
    value = _SANITIZE.sub("_", (raw or "").strip())
    return value or "x"


def fsm_state_id(node_id: str) -> str:
    return f"s_{sanitize_id(node_id)}"


def fsm_transition_id(origin_id: str) -> str:
    return f"t_{sanitize_id(origin_id)}"


def wait_node_id(state_id: str) -> str:
    return f"node_wait_{sanitize_id(state_id)}"


def do_node_id(transition_id: str, action_id: str) -> str:
    return f"node_do_{sanitize_id(transition_id)}_{sanitize_id(action_id)}"


def decide_node_id(state_id: str, event: str) -> str:
    return f"node_decide_{sanitize_id(state_id)}_{sanitize_id(event)}"


def end_node_id(state_id: str) -> str:
    return f"node_end_{sanitize_id(state_id)}"


def edge_id(from_id: str, to_id: str, index: int) -> str:
    return f"edge_{sanitize_id(from_id)}_{sanitize_id(to_id)}_{index}"


def branch_id(transition_id: str, index: int) -> str:
    return f"branch_{sanitize_id(transition_id or str(index))}_{index}"
