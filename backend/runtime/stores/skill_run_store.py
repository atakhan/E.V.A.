from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from domain.agent import SkillRun, SkillRunStatus


@dataclass
class InMemoryStore:
    runs: dict[str, SkillRun] = field(default_factory=dict)
    by_conversation: dict[str, str] = field(default_factory=dict)


class SkillRunStore(Protocol):
    def get_run(self, run_id: str) -> SkillRun | None: ...

    def save_run(self, run: SkillRun) -> None: ...

    def find_waiting_by_conversation(self, conversation_id: str) -> SkillRun | None: ...

    def find_waiting_runs(self, correlation_key: str, value: str) -> list[SkillRun]: ...

    def map_conversation(self, conversation_id: str, run_id: str) -> None: ...


def store_get_run(store: SkillRunStore | InMemoryStore, run_id: str) -> SkillRun | None:
    if isinstance(store, InMemoryStore):
        return store.runs.get(run_id)
    return store.get_run(run_id)


def store_save_run(store: SkillRunStore | InMemoryStore, run: SkillRun) -> None:
    if isinstance(store, InMemoryStore):
        store.runs[run.id] = run
        conversation_id = run.vars.get("conversation_id")
        if isinstance(conversation_id, str) and conversation_id:
            store.by_conversation[conversation_id] = run.id
        return
    store.save_run(run)
    conversation_id = run.vars.get("conversation_id")
    if isinstance(conversation_id, str) and conversation_id:
        store.map_conversation(conversation_id, run.id)


def store_find_waiting_runs(
    store: SkillRunStore | InMemoryStore,
    correlation_key: str,
    value: str,
) -> list[SkillRun]:
    if isinstance(store, InMemoryStore):
        if correlation_key == "conversation_id":
            run_id = store.by_conversation.get(value)
            if not run_id:
                return []
            existing = store.runs.get(run_id)
            if existing and existing.status in (SkillRunStatus.waiting, SkillRunStatus.running):
                return [existing]
        matches: list[SkillRun] = []
        for run in store.runs.values():
            if run.status not in (SkillRunStatus.waiting, SkillRunStatus.running):
                continue
            if run.params.get(correlation_key) == value or run.vars.get(correlation_key) == value:
                matches.append(run)
        return matches
    return store.find_waiting_runs(correlation_key, value)


def store_find_waiting(store: SkillRunStore | InMemoryStore, conversation_id: str) -> SkillRun | None:
    if isinstance(store, InMemoryStore):
        run_id = store.by_conversation.get(conversation_id)
        if not run_id:
            return None
        existing = store.runs.get(run_id)
        if existing and existing.status in (SkillRunStatus.waiting, SkillRunStatus.running):
            return existing
        return None
    return store.find_waiting_by_conversation(conversation_id)
