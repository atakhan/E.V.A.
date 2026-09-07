from __future__ import annotations

from typing import Any


def normalize_focus(raw: dict[str, Any]) -> dict[str, Any]:
    """Canonical camelCase focus; keep extra client keys (topicId, …)."""
    focus = dict(raw)
    if "openEntityId" not in focus and focus.get("open_entity_id"):
        focus["openEntityId"] = focus.pop("open_entity_id")
    elif "open_entity_id" in focus:
        focus.pop("open_entity_id", None)
    if "selectedEntityIds" not in focus and focus.get("selected_entity_ids") is not None:
        focus["selectedEntityIds"] = focus.pop("selected_entity_ids")
    elif "selected_entity_ids" in focus:
        focus.pop("selected_entity_ids", None)
    selected = focus.get("selectedEntityIds") or []
    if not isinstance(selected, list):
        selected = [selected]
    focus["selectedEntityIds"] = [str(item) for item in selected if item]
    open_id = focus.get("openEntityId")
    if open_id:
        focus["openEntityId"] = str(open_id)
    view = focus.get("view")
    if view:
        focus["view"] = str(view)
    return focus


def normalize_web_act(
    payload: dict[str, Any],
    *,
    actor_id: str | None = None,
    focus: dict[str, Any] | None = None,
    intent: str | None = None,
    entity_ids: list[Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Lift a human act into payload + metadata.focus. Correlation stays for later.

    ``actor_id`` becomes ``user_id`` (EVENT §10). Focus is copied to metadata, not
    correlation. ``entity_ids`` stay on the payload; first id fills ``entity_id``.
    """
    out = dict(payload)
    metadata: dict[str, Any] = {}

    actor = actor_id or out.get("actor_id") or out.get("user_id")
    if actor:
        out["actor_id"] = str(actor)
        out.setdefault("user_id", str(actor))
        out.setdefault("sender_id", str(actor))

    intent_val = intent if intent is not None else out.get("intent")
    if intent_val:
        out["intent"] = str(intent_val)

    ids = entity_ids if entity_ids is not None else out.get("entity_ids")
    if ids:
        clean = [str(item) for item in ids if item]
        out["entity_ids"] = clean
        if clean and not out.get("entity_id"):
            out["entity_id"] = clean[0]

    focus_val = focus if focus is not None else out.get("focus")
    if isinstance(focus_val, dict) and focus_val:
        normalized = normalize_focus(focus_val)
        out["focus"] = normalized
        metadata["focus"] = normalized
        if not out.get("entity_ids"):
            selected = list(normalized.get("selectedEntityIds") or [])
            open_id = normalized.get("openEntityId")
            derived = selected or ([str(open_id)] if open_id else [])
            if derived:
                out["entity_ids"] = derived
                out.setdefault("entity_id", derived[0])

    return out, metadata
