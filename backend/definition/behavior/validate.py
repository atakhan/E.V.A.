from __future__ import annotations

from typing import Any

from definition.behavior.graph import node_map, outgoing_edges, successors


def validate_behavior_graph(
    graph: dict[str, Any] | None,
    *,
    action_ids: set[str] | None = None,
    skill_id: str = "",
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not graph:
        return issues

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    nodes_by_id = node_map(graph)
    entry = str(graph.get("entry") or "")

    if not nodes:
        issues.append(
            {
                "code": "behavior_empty",
                "severity": "warning",
                "message": "Behavior Graph пуст",
                "nodeId": None,
            }
        )
        return issues

    if entry and entry not in nodes_by_id:
        issues.append(
            {
                "code": "invalid_entry",
                "severity": "error",
                "message": f"entry «{entry}» не найден среди узлов",
                "nodeId": entry,
            }
        )
    elif entry:
        entry_type = nodes_by_id[entry].get("type")
        if entry_type != "wait":
            issues.append(
                {
                    "code": "entry_not_wait",
                    "severity": "error",
                    "message": "entry в v1 должен быть wait",
                    "nodeId": entry,
                }
            )

    known = set(nodes_by_id)
    for edge in edges:
        if edge.get("from") not in known:
            issues.append(
                {
                    "code": "dangling_edge_from",
                    "severity": "error",
                    "message": f"ребро {edge.get('id')}: неизвестный from",
                    "nodeId": edge.get("from"),
                }
            )
        if edge.get("to") not in known:
            issues.append(
                {
                    "code": "dangling_edge_to",
                    "severity": "error",
                    "message": f"ребро {edge.get('id')}: неизвестный to",
                    "nodeId": edge.get("to"),
                }
            )

    for node in nodes:
        node_id = str(node.get("id") or "")
        node_type = node.get("type")
        if node_type == "do" and not str(node.get("actionId") or "").strip():
            issues.append(
                {
                    "code": "do_missing_action",
                    "severity": "error",
                    "message": f"{node_id}: do без actionId",
                    "nodeId": node_id,
                }
            )
        if node_type == "do" and action_ids is not None:
            action_id = str(node.get("actionId") or "").strip()
            if action_id and action_id not in action_ids:
                issues.append(
                    {
                        "code": "unknown_action",
                        "severity": "error",
                        "message": f"{node_id}: неизвестный action «{action_id}»",
                        "nodeId": node_id,
                    }
                )
        if node_type == "wait":
            wait_for = node.get("waitFor") or {}
            kind = wait_for.get("type")
            if kind == "event" and not str(wait_for.get("event") or "").strip():
                issues.append(
                    {
                        "code": "wait_missing_event",
                        "severity": "error",
                        "message": f"{node_id}: wait.event без event",
                        "nodeId": node_id,
                    }
                )
            if kind == "action" and not str(wait_for.get("actionId") or "").strip():
                issues.append(
                    {
                        "code": "wait_missing_action",
                        "severity": "error",
                        "message": f"{node_id}: wait.action без actionId",
                        "nodeId": node_id,
                    }
                )
            if kind == "condition" and not str(wait_for.get("event") or "").strip():
                issues.append(
                    {
                        "code": "wait_missing_event",
                        "severity": "error",
                        "message": f"{node_id}: wait.condition без event",
                        "nodeId": node_id,
                    }
                )
            outs = outgoing_edges(graph, node_id)
            if len(outs) > 1:
                issues.append(
                    {
                        "code": "wait_multiple_next",
                        "severity": "error",
                        "message": f"{node_id}: wait может иметь одно исходящее ребро",
                        "nodeId": node_id,
                    }
                )
        if node_type == "do":
            outs = outgoing_edges(graph, node_id)
            if len(outs) > 1:
                issues.append(
                    {
                        "code": "do_multiple_next",
                        "severity": "error",
                        "message": f"{node_id}: do может иметь одно исходящее ребро",
                        "nodeId": node_id,
                    }
                )
        if node_type == "end" and outgoing_edges(graph, node_id):
            issues.append(
                {
                    "code": "end_has_outgoing",
                    "severity": "error",
                    "message": f"{node_id}: end не должен иметь исходящих рёбер",
                    "nodeId": node_id,
                }
            )
        if node_type == "decide":
            branches = node.get("branches") or []
            if not branches:
                issues.append(
                    {
                        "code": "decide_no_branches",
                        "severity": "error",
                        "message": f"{node_id}: decide без веток",
                        "nodeId": node_id,
                    }
                )
            for branch in branches:
                target = str(branch.get("to") or "")
                if target not in known:
                    issues.append(
                        {
                            "code": "dangling_branch",
                            "severity": "error",
                            "message": f"{node_id}: ветка на неизвестный узел",
                            "nodeId": node_id,
                        }
                    )
                elif nodes_by_id[target].get("type") == "decide":
                    issues.append(
                        {
                            "code": "nested_decide",
                            "severity": "error",
                            "message": f"{node_id}: вложенный decide в v1 запрещён",
                            "nodeId": node_id,
                        }
                    )

        for _kind, item in successors(graph, node_id):
            target = nodes_by_id.get(str(item.get("to") or ""))
            if node_type == "wait" and (node.get("waitFor") or {}).get("type") == "condition":
                if target and target.get("type") == "decide":
                    issues.append(
                        {
                            "code": "condition_wait_to_decide",
                            "severity": "error",
                            "message": f"{node_id}: wait.condition не может сразу переходить в decide",
                            "nodeId": node_id,
                        }
                    )

    _ = skill_id
    return issues
