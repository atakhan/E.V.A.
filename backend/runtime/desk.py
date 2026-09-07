from __future__ import annotations

import json
from typing import Any

from domain.agent import SkillRun
from domain.events import Event, ToolResult


def overlay_entity_from_desk(run: SkillRun, snapshot: dict[str, Any]) -> None:
    entity_id = str(run.vars.get("entity_id") or run.vars.get("request_id") or "")
    workspace = snapshot.get("workspace") if isinstance(snapshot.get("workspace"), dict) else snapshot
    requests = workspace.get("requests") if isinstance(workspace, dict) else None
    if not entity_id or not isinstance(requests, list):
        return
    for item in requests:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") != entity_id:
            continue
        for key in ("quantity", "unit", "title", "status", "site"):
            if item.get(key) is not None:
                run.vars[key] = item[key]
        return


def refresh_desk_snapshot(run: SkillRun, event: Event, registry: Any) -> None:
    """Read the desk into run.vars before speech/decision. No-op without web_client."""
    if event.type.startswith("action.") or event.type == "runtime.continue":
        return
    getter = getattr(registry, "get", None)
    if getter is None:
        return
    tool = getter("web_client")
    command = getattr(tool, "cmd_get_snapshot", None) if tool is not None else None
    if command is None:
        return
    result = command({}, {"vars": run.vars})
    if not isinstance(result, ToolResult) or not result.ok:
        return
    snapshot = (result.data or {}).get("snapshot")
    if not isinstance(snapshot, dict):
        return
    run.vars["_desk"] = snapshot
    run.vars["_desk_text"] = json.dumps(snapshot, ensure_ascii=False)[:8000]
    overlay_entity_from_desk(run, snapshot)
