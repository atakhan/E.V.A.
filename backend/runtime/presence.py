from __future__ import annotations

from typing import Any

from domain.agent import SkillRunStatus

_SKILL_LABELS = {
    "razgovor": "Разговор",
    "chat_with_supplier": "Разговор",
    "process_supplier_request": "Разбор заявок",
}

_STATUS_LABELS = {
    SkillRunStatus.waiting.value: "ждёт вас",
    SkillRunStatus.running.value: "занят",
}


def presence_from_runs(runs: list) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for run in runs:
        status = run.status.value if hasattr(run.status, "value") else str(run.status)
        items.append(
            {
                "skillRunId": run.id,
                "skillId": run.skill_id,
                "status": status,
                "currentState": run.current_state,
                "label": _SKILL_LABELS.get(run.skill_id, run.skill_id),
                "busy": _STATUS_LABELS.get(status, status),
            }
        )
    return items


def presence_for_conversation(session: Any, conversation_id: str) -> list[dict[str, Any]]:
    if session is None or not conversation_id:
        return []
    from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore

    store = PostgresSkillRunStore(session)
    runs = store.find_waiting_runs("conversation_id", conversation_id)
    return presence_from_runs(runs)
