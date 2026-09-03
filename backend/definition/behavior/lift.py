from __future__ import annotations

from typing import Any

from definition.behavior.graph import (
    EVENT_TITLES,
    action_id_from_completed_event,
    default_wait_title,
    empty_behavior_graph,
)
from definition.behavior.ids import (
    GRAPH_VERSION,
    branch_id,
    decide_node_id,
    do_node_id,
    edge_id,
    end_node_id,
    wait_node_id,
)


def lift_fsm_to_behavior(
    states: list[dict[str, Any]] | None,
    initial: str | None,
) -> dict[str, Any]:
    """Deterministic FSM → Behavior Graph. Completion states after do are not waits."""
    states = list(states or [])
    if not states:
        return empty_behavior_graph()

    state_by_id = {str(state["id"]): state for state in states if state.get("id")}
    incoming_actions: dict[str, set[str]] = {key: set() for key in state_by_id}
    for state in states:
        for transition in state.get("transitions") or []:
            target = str(transition.get("to") or "")
            incoming_actions.setdefault(target, set()).update(
                str(action) for action in (transition.get("actions") or []) if action
            )

    def is_completion(state_id: str) -> bool:
        state = state_by_id.get(state_id)
        if state is None:
            return False
        transitions = list(state.get("transitions") or [])
        if not transitions:
            return False
        completed = [action_id_from_completed_event(str(item.get("event") or "")) for item in transitions]
        if any(item is None for item in completed):
            return False
        fired = incoming_actions.get(state_id) or set()
        return bool(set(completed) & fired)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    known_nodes: set[str] = set()
    wait_for_state: dict[str, str] = {}
    processed_outgoing: set[str] = set()
    edge_index = [0]

    def add_node(node: dict[str, Any]) -> None:
        node_id = str(node["id"])
        if node_id in known_nodes:
            return
        known_nodes.add(node_id)
        nodes.append(node)

    def add_edge(from_id: str, to_id: str, kind: str = "next") -> str:
        edge_index[0] += 1
        identifier = edge_id(from_id, to_id, edge_index[0])
        edges.append({"id": identifier, "from": from_id, "to": to_id, "kind": kind})
        return identifier

    def layout_from(state: dict[str, Any], order: int) -> dict[str, Any]:
        return {
            "story": {"x": 48, "y": 48 + order * 140, "width": 280, "height": 96},
            "logic": {
                "x": float(state.get("x") or 0),
                "y": float(state.get("y") or 0),
                "width": float(state.get("width") or 160),
                "height": float(state.get("height") or 80),
            },
        }

    def classify_event(event: str) -> dict[str, Any]:
        action_id = action_id_from_completed_event(event)
        if action_id:
            return {"type": "action", "actionId": action_id}
        if event == "channel.message.received":
            return {"type": "input", "event": event}
        return {"type": "event", "event": event}

    def ensure_wait(state_id: str) -> str:
        if state_id in wait_for_state:
            return wait_for_state[state_id]
        state = state_by_id[state_id]
        transitions = list(state.get("transitions") or [])
        order = len(nodes)
        if state.get("final") and not transitions:
            identifier = end_node_id(state_id)
            add_node(
                {
                    "id": identifier,
                    "type": "end",
                    "title": str(state.get("name") or "Задача завершена"),
                    "layout": layout_from(state, order),
                }
            )
            wait_for_state[state_id] = identifier
            return identifier
        event = str(transitions[0].get("event") or "event") if transitions else "event"
        wait_for = classify_event(event)
        identifier = wait_node_id(state_id)
        title = str(state.get("name") or "").strip() or default_wait_title(wait_for)
        if title == state_id and wait_for.get("type") in {"event", "input"}:
            title = EVENT_TITLES.get(str(wait_for.get("event") or event), title)
        add_node(
            {
                "id": identifier,
                "type": "wait",
                "title": title,
                "waitFor": wait_for,
                "layout": layout_from(state, order),
            }
        )
        wait_for_state[state_id] = identifier
        return identifier

    def emit_action_chain(transition: dict[str, Any]) -> tuple[str | None, str | None]:
        actions = [str(action) for action in (transition.get("actions") or []) if action]
        if not actions:
            return None, None
        transition_key = str(transition.get("id") or f"{transition.get('event')}_{transition.get('to')}")
        created: list[str] = []
        for action in actions:
            identifier = do_node_id(transition_key, action)
            add_node(
                {
                    "id": identifier,
                    "type": "do",
                    "title": action,
                    "actionId": action,
                }
            )
            created.append(identifier)
        for index in range(len(created) - 1):
            add_edge(created[index], created[index + 1], "next")
        return created[0], created[-1]

    def connect_target(from_node_id: str, transition: dict[str, Any], *, entry_wait: str) -> None:
        target_state_id = str(transition.get("to") or "")
        if not target_state_id:
            return
        if is_completion(target_state_id):
            process_outgoing(target_state_id, from_node_id, entry_wait)
            return
        target_node = ensure_wait(target_state_id)
        kind = "loop" if target_node == entry_wait else "next"
        if from_node_id != target_node:
            add_edge(from_node_id, target_node, kind)
        process_outgoing(target_state_id, target_node, entry_wait)

    def process_outgoing(state_id: str, from_node_id: str, entry_wait: str) -> None:
        if state_id in processed_outgoing:
            return
        processed_outgoing.add(state_id)
        state = state_by_id.get(state_id)
        if state is None:
            return
        transitions = list(state.get("transitions") or [])
        if not transitions:
            return
        needs_decide = len(transitions) > 1 or any(
            str(item.get("guard") or "").strip() for item in transitions
        )
        if needs_decide:
            event = str(transitions[0].get("event") or "event")
            identifier = decide_node_id(state_id, event)
            branches: list[dict[str, Any]] = []
            for index, transition in enumerate(transitions):
                first, last = emit_action_chain(transition)
                trans_id = str(transition.get("id") or f"{state_id}_{index}")
                label = _branch_label(transition, index, len(transitions))
                if first:
                    branches.append(
                        {
                            "id": branch_id(trans_id, index),
                            "label": label,
                            "guard": str(transition.get("guard") or "").strip(),
                            "to": first,
                        }
                    )
                    connect_target(last or first, transition, entry_wait=entry_wait)
                else:
                    target_state_id = str(transition.get("to") or "")
                    if is_completion(target_state_id):
                        # no actions and completion — follow outgoing later
                        target_node = from_node_id
                    else:
                        target_node = ensure_wait(target_state_id) if target_state_id else from_node_id
                    branches.append(
                        {
                            "id": branch_id(trans_id, index),
                            "label": label,
                            "guard": str(transition.get("guard") or "").strip(),
                            "to": target_node,
                        }
                    )
                    if first is None and target_state_id:
                        if is_completion(target_state_id):
                            process_outgoing(target_state_id, from_node_id, entry_wait)
                        else:
                            process_outgoing(target_state_id, target_node, entry_wait)
            add_node(
                {
                    "id": identifier,
                    "type": "decide",
                    "title": "",
                    "question": "Какая ветка?",
                    "branches": branches,
                }
            )
            add_edge(from_node_id, identifier, "next")
            return

        transition = transitions[0]
        first, last = emit_action_chain(transition)
        if first:
            add_edge(from_node_id, first, "next")
            connect_target(last or first, transition, entry_wait=entry_wait)
            return
        connect_target(from_node_id, transition, entry_wait=entry_wait)

    start = str(initial or "")
    if not start or start not in state_by_id:
        start = str(states[0]["id"])
    if is_completion(start):
        # unusual: still wrap as wait
        pass
    entry = ensure_wait(start)
    process_outgoing(start, entry, entry)
    return {
        "version": GRAPH_VERSION,
        "entry": entry,
        "nodes": nodes,
        "edges": edges,
    }


def _branch_label(transition: dict[str, Any], index: int, total: int) -> str:
    guard = str(transition.get("guard") or "").strip()
    if not guard:
        return "Иначе"
    if total == 2:
        return "Да" if index == 0 else "Нет"
    return f"Ветка {index + 1}"
