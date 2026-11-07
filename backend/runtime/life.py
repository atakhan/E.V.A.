"""Life thread — the agent's continuous root Skill Run.

Ontology: agent is alive iff skill `life` exists and one active life run is waiting/running.
Other skills are episodes linked via parent_run_id / _life_run_id.
The package `backend/runtime/` is the execution machine, not the product concept.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from definition.system_skills import LIFE
from domain.agent import SkillRun, SkillRunStatus
from runtime.skill_run_query import SkillRunListFilters
from runtime.stores.skill_run_store import InMemoryStore, store_get_run, store_save_run

if TYPE_CHECKING:
    from runtime.runtime_service import RuntimeService
    from sqlalchemy.orm import Session

_ACTIVE = (SkillRunStatus.waiting, SkillRunStatus.running)


def publication_has_life(body: dict[str, Any] | None) -> bool:
    if not body:
        return False
    for item in body.get("skills") or []:
        if not isinstance(item, dict):
            continue
        if item.get("id") == LIFE or item.get("systemRole") == LIFE:
            return True
    return False


def find_active_life_run(store: Any, agent_slug: str) -> SkillRun | None:
    """Return the active life Skill Run for this agent, if any."""
    if isinstance(store, InMemoryStore):
        for run in store.runs.values():
            if run.skill_id != LIFE or run.status not in _ACTIVE:
                continue
            slug = run.vars.get("_agent_slug") or ""
            if not agent_slug or slug == agent_slug:
                return run
        return None

    list_runs = getattr(store, "list_runs", None)
    get_run = getattr(store, "get_run", None)
    if not callable(list_runs) or not callable(get_run):
        return None

    items, _ = list_runs(
        SkillRunListFilters(
            agent_slug=agent_slug or None,
            skill_id=LIFE,
            active_only=True,
            limit=1,
        )
    )
    if not items:
        return None
    return store_get_run(store, items[0].skill_run_id)


def ensure_life_run_on_service(service: RuntimeService) -> SkillRun | None:
    """Idempotently ensure one waiting/running life thread on this service's store."""
    body = service.context.publication_body or service.context.agent_body
    if not publication_has_life(body):
        return None

    slug = service.context.agent_slug
    existing = find_active_life_run(service.context.store, slug)
    if existing is not None:
        return existing

    life_service = service if service.context.catalog.skill.id == LIFE else service._service_for_skill(LIFE)
    if life_service is None:
        return None

    skill = life_service.context.catalog.skill
    run = SkillRun(
        skill_id=LIFE,
        skill_version=life_service.context.publication_version,
        current_state=skill.initial,
        history=[skill.initial],
        status=SkillRunStatus.waiting,
        vars={
            "_agent_id": life_service.context.agent_id,
            "_agent_slug": life_service.context.agent_slug,
        },
    )
    store_save_run(life_service.context.store, run)
    return run


def ensure_life_run_for_agent(session: Session, agent_slug: str) -> SkillRun | None:
    """Ensure life thread after publish (or any session-scoped wake)."""
    from runtime.runtime_factory import build_runtime_service

    try:
        service = build_runtime_service(session, agent_slug=agent_slug, skill_id=LIFE)
    except KeyError:
        return None
    return ensure_life_run_on_service(service)


def attach_life_parent(run: SkillRun, life_run: SkillRun | None) -> None:
    """Link an episode run to the life thread."""
    if life_run is None or run.skill_id == LIFE:
        return
    run.params["parent_run_id"] = life_run.id
    run.vars["parent_run_id"] = life_run.id
    run.vars["_life_run_id"] = life_run.id
