from __future__ import annotations

from typing import Any

from definition.behavior.graph import leaving_event, node_map, successors
from definition.behavior.ids import COMPILER_VERSION, fsm_state_id, fsm_transition_id
from definition.behavior.validate import validate_behavior_graph


def compile_behavior(
    graph: dict[str, Any] | None,
    *,
    compiled_at: str | None = None,
    action_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Compile Behavior Graph → execution artifact. Deterministic. No wall-clock in ids."""
    errors = validate_behavior_graph(graph, action_ids=action_ids)
    blocking = [issue for issue in errors if issue.get("severity") == "error"]
    if not graph or blocking:
        return {"ok": False, "errors": errors, "artifact": None}

    nodes = node_map(graph)
    entry = str(graph.get("entry") or "")
    ordered = _ordered_state_nodes(graph, nodes, entry)
    states: list[dict[str, Any]] = []
    for index, node in enumerate(ordered):
        states.append(
            {
                "id": fsm_state_id(str(node["id"])),
                "name": str(node.get("title") or node["id"]),
                "originNodeId": str(node["id"]),
                "onEnter": [],
                "final": node.get("type") == "end",
                "transitions": [],
                "x": index * 220,
                "y": 0,
                "width": 160,
                "height": 80,
            }
        )
    by_origin = {state["originNodeId"]: state for state in states}

    for node in ordered:
        if node.get("type") == "end":
            continue
        event, base_guard = leaving_event(node)
        if not event:
            continue
        items = successors(graph, str(node["id"]))
        for _kind, item in items:
            origin_id = str(item.get("id") or "")
            target_id = str(item.get("to") or "")
            _emit_leaf(nodes, by_origin, node, event, base_guard, origin_id, target_id)

    initial = ""
    if entry and entry in by_origin:
        initial = by_origin[entry]["id"]
    elif states:
        initial = states[0]["id"]

    artifact: dict[str, Any] = {
        "compilerVersion": COMPILER_VERSION,
        "initial": initial,
        "states": states,
    }
    if compiled_at:
        artifact["compiledAt"] = compiled_at
    return {"ok": True, "errors": errors, "artifact": artifact}


def _ordered_state_nodes(
    graph: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    entry: str,
) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    queue: list[str] = [entry] if entry else []
    while queue:
        node_id = queue.pop(0)
        if node_id in seen:
            continue
        seen.add(node_id)
        node = nodes.get(node_id)
        if node is None:
            continue
        if node.get("type") != "decide":
            ordered.append(node)
        for _kind, item in successors(graph, node_id):
            target = str(item.get("to") or "")
            if target:
                queue.append(target)
    for node in sorted(nodes.values(), key=lambda item: str(item.get("id") or "")):
        node_id = str(node.get("id") or "")
        if node_id not in seen and node.get("type") != "decide":
            ordered.append(node)
    return ordered


def _emit_leaf(
    nodes: dict[str, dict[str, Any]],
    by_origin: dict[str, dict[str, Any]],
    source: dict[str, Any],
    event: str,
    guard: str,
    origin_edge_id: str,
    target_id: str,
) -> None:
    target = nodes.get(target_id)
    source_state = by_origin.get(str(source["id"]))
    if target is None or source_state is None:
        return
    if target.get("type") == "decide":
        for branch in target.get("branches") or []:
            branch_guard = str(branch.get("guard") or "")
            _emit_leaf(
                nodes,
                by_origin,
                source,
                event,
                branch_guard or guard,
                str(branch.get("id") or origin_edge_id),
                str(branch.get("to") or ""),
            )
        return
    if target.get("type") == "do":
        actions = [str(target.get("actionId") or "")]
        to_id = fsm_state_id(str(target["id"]))
    else:
        actions = []
        to_id = fsm_state_id(str(target["id"]))
    source_state["transitions"].append(
        {
            "id": fsm_transition_id(origin_edge_id),
            "event": event,
            "guard": guard or "",
            "actions": [item for item in actions if item],
            "to": to_id,
            "originNodeId": str(source["id"]),
            "originEdgeId": origin_edge_id,
        }
    )
