from __future__ import annotations

from typing import Any

from definition.behavior.graph import node_map, successors


def behavior_narrative(graph: dict[str, Any] | None) -> str:
    """Deterministic story text. Not LLM."""
    if not graph:
        return ""
    nodes = node_map(graph)
    entry = str(graph.get("entry") or "")
    if not entry or entry not in nodes:
        return ""
    lines: list[str] = []
    seen: set[str] = set()

    def title_of(node_id: str) -> str:
        node = nodes.get(node_id) or {}
        return str(node.get("title") or node.get("question") or node_id).rstrip(".")

    def walk(node_id: str) -> None:
        if node_id in seen:
            lines.append(f"Возвращаюсь к «{title_of(node_id)}».")
            return
        seen.add(node_id)
        node = nodes.get(node_id)
        if node is None:
            return
        node_type = node.get("type")
        if node_type == "wait":
            lines.append(f"Когда {title_of(node_id)}.")
        elif node_type == "do":
            lines.append(f"Я {title_of(node_id)}.")
        elif node_type == "decide":
            question = str(node.get("question") or "Что дальше?").rstrip("?")
            lines.append(f"{question}?")
            for branch in node.get("branches") or []:
                label = str(branch.get("label") or "ветка")
                lines.append(f"Если {label}:")
                target = str(branch.get("to") or "")
                if target:
                    walk(target)
            return
        elif node_type == "end":
            lines.append("Задача завершена.")
            return
        for _kind, item in successors(graph, node_id):
            target = str(item.get("to") or "")
            if target:
                walk(target)

    walk(entry)
    return " ".join(lines)
