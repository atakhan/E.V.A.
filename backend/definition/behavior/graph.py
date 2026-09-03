from __future__ import annotations

from typing import Any

from definition.behavior.ids import GRAPH_VERSION


def empty_behavior_graph() -> dict[str, Any]:
    return {"version": GRAPH_VERSION, "entry": "", "nodes": [], "edges": []}


def node_map(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(node["id"]): node for node in graph.get("nodes") or [] if node.get("id")}


def outgoing_edges(graph: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    edges = [edge for edge in graph.get("edges") or [] if edge.get("from") == node_id]
    return sorted(edges, key=lambda item: str(item.get("id") or ""))


def successors(graph: dict[str, Any], node_id: str) -> list[tuple[str, dict[str, Any]]]:
    node = node_map(graph).get(node_id)
    if node is None:
        return []
    if node.get("type") == "decide":
        return [("branch", branch) for branch in node.get("branches") or []]
    return [("edge", edge) for edge in outgoing_edges(graph, node_id)]


def action_id_from_completed_event(event: str) -> str | None:
    prefix = "action."
    suffix = ".completed"
    if event.startswith(prefix) and event.endswith(suffix):
        middle = event[len(prefix) : -len(suffix)]
        return middle or None
    return None


def wait_event_and_guard(node: dict[str, Any]) -> tuple[str, str]:
    wait_for = node.get("waitFor") or {}
    kind = wait_for.get("type")
    if kind == "event":
        return str(wait_for.get("event") or "event"), ""
    if kind == "action":
        action_id = str(wait_for.get("actionId") or "")
        return f"action.{action_id}.completed", ""
    if kind == "input":
        return str(wait_for.get("event") or "channel.message.received"), ""
    if kind == "condition":
        return str(wait_for.get("event") or "event"), str(wait_for.get("expression") or "")
    return "event", ""


def leaving_event(node: dict[str, Any]) -> tuple[str | None, str]:
    node_type = node.get("type")
    if node_type == "wait":
        return wait_event_and_guard(node)
    if node_type == "do":
        return f"action.{node.get('actionId')}.completed", ""
    return None, ""


def default_wait_title(wait_for: dict[str, Any]) -> str:
    kind = wait_for.get("type")
    if kind == "event":
        event = str(wait_for.get("event") or "")
        return EVENT_TITLES.get(event, event or "Когда случается событие")
    if kind == "action":
        return f"Жду завершения «{wait_for.get('actionId')}»"
    if kind == "input":
        return EVENT_TITLES.get(
            str(wait_for.get("event") or "channel.message.received"),
            "Жду ответа",
        )
    if kind == "condition":
        return "Жду, пока выполнится условие"
    return "Жду"


EVENT_TITLES = {
    "channel.message.received": "Когда приходит новое сообщение",
    "channel.message.sent": "Когда сообщение отправлено",
    "supplier.reply.received": "Когда приходит ответ поставщика",
    "request.created": "Когда создана заявка",
    "request.updated": "Когда заявка обновлена",
    "invoice.received": "Когда приходит счёт",
    "human.request.approved": "Когда запрос подтверждён",
    "human.request.corrected": "Когда запрос исправлен",
    "shipment.updated": "Когда поставка обновлена",
    "timer.elapsed": "Когда срабатывает таймер",
}


def normalize_guard(guard: str | None) -> str:
    return " ".join((guard or "").split())
