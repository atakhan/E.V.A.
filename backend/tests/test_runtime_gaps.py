from __future__ import annotations

import uuid
from typing import Any

import pytest

from domain.events import Event
from runtime.skill_routing import find_skills_for_event
from tests.conftest import new_ephemeral_agent_slug

SKILL_ID = "test_skill"
START_EVENT = "request.started"


def _minimal_agent_body(*, transition_to: str = "done") -> dict[str, Any]:
    return {
        "skills": [
            {
                "id": SKILL_ID,
                "name": "Test skill",
                "version": "1.0.0",
                "initial": "new",
                "params": [],
                "states": [
                    {
                        "id": "new",
                        "onEnter": [],
                        "final": False,
                        "transitions": [{"event": START_EVENT, "to": transition_to}],
                    },
                    {"id": "done", "onEnter": [], "final": True, "transitions": []},
                    {"id": "PINNED_TARGET", "onEnter": [], "final": True, "transitions": []},
                    {"id": "OTHER_TARGET", "onEnter": [], "final": True, "transitions": []},
                ],
            }
        ],
        "actions": [],
        "tools": [],
    }


def _seed_minimal_agent(agent_service, slug: str, *, transition_to: str = "done") -> None:
    body = agent_service.get_agent_by_slug(slug)
    assert body is not None
    draft = {**body, **_minimal_agent_body(transition_to=transition_to)}
    agent_service.upsert_draft(slug, draft)


def _create_test_agent(session) -> str:
    from definition.services.agent_service import AgentService

    slug = new_ephemeral_agent_slug()
    AgentService(session).create_agent(name="Runtime test", slug=slug, description="runtime gaps")
    return slug


def test_find_skills_for_event_multiple():
    body = {
        "skills": [
            {
                "id": "skill_a",
                "initial": "new",
                "states": [
                    {
                        "id": "new",
                        "transitions": [{"event": "invoice.received", "to": "done"}],
                    }
                ],
            },
            {
                "id": "skill_b",
                "initial": "start",
                "states": [
                    {
                        "id": "start",
                        "transitions": [{"event": "invoice.received", "to": "done"}],
                    }
                ],
            },
        ]
    }
    matches = find_skills_for_event(body, "invoice.received")
    assert set(matches) == {"skill_a", "skill_b"}


def test_find_skills_for_event_no_match():
    body = {
        "skills": [
            {
                "id": "skill_a",
                "initial": "new",
                "states": [{"id": "new", "transitions": [{"event": "other.event", "to": "done"}]}],
            }
        ]
    }
    assert find_skills_for_event(body, "invoice.received") == []


@pytest.mark.integration
def test_version_pinning_on_resume():
    from app.deps import session_scope
    from definition.services.agent_service import AgentService
    from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
    from runtime.runtime_factory import build_runtime_service, resolve_publication

    slug: str | None = None
    try:
        with session_scope() as session:
            slug = _create_test_agent(session)
            agent_service = AgentService(session)
            _seed_minimal_agent(agent_service, slug, transition_to="PINNED_TARGET")
            agent_service.publish(slug)
            v1 = resolve_publication(agent_service, slug, None).version

        with session_scope() as session:
            runtime_v1 = build_runtime_service(
                session, agent_slug=slug, skill_id=SKILL_ID, publication_version=v1
            )
            result = runtime_v1.route(
                Event(
                    type=START_EVENT,
                    source="test",
                    payload={"conversation_id": f"pin-{uuid.uuid4().hex[:8]}"},
                )
            )
            run_id = result.run.id
            pinned_version = result.run.skill_version
            assert result.run.current_state == "PINNED_TARGET"

        with session_scope() as session:
            agent_service = AgentService(session)
            _seed_minimal_agent(agent_service, slug, transition_to="OTHER_TARGET")
            agent_service.publish(slug)

        with session_scope() as session:
            store = PostgresSkillRunStore(session)
            run = store.get_run(run_id)
            assert run is not None
            assert run.skill_version == pinned_version
            assert run.current_state == "PINNED_TARGET"

            runtime_resume = build_runtime_service(
                session,
                agent_slug=slug,
                skill_id=SKILL_ID,
                publication_version=pinned_version,
            )
            initial_state = runtime_resume.context.catalog.skill.get_state("new")
            assert initial_state is not None
            assert initial_state.transitions[0].to == "PINNED_TARGET"
    finally:
        if slug:
            with session_scope() as session:
                AgentService(session).delete_agent(slug)


@pytest.mark.integration
def test_optimistic_locking_conflict():
    from app.deps import session_scope
    from definition.services.agent_service import AgentService
    from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore
    from runtime.exceptions import ConcurrentUpdateError
    from runtime.runtime_factory import build_runtime_service

    slug: str | None = None
    try:
        with session_scope() as session:
            slug = _create_test_agent(session)
            agent_service = AgentService(session)
            _seed_minimal_agent(agent_service, slug)
            agent_service.publish(slug)

        with session_scope() as session:
            runtime = build_runtime_service(session, agent_slug=slug, skill_id=SKILL_ID)
            result = runtime.route(
                Event(
                    type=START_EVENT,
                    source="test",
                    payload={"conversation_id": f"lock-{uuid.uuid4().hex[:8]}"},
                )
            )
            run_id = result.run.id

        with session_scope() as session:
            store = PostgresSkillRunStore(session)
            run = store.get_run(run_id)
            assert run is not None
            copy_a = run.model_copy(deep=True)
            copy_b = run.model_copy(deep=True)
            copy_a.vars["marker"] = "a"
            store.save_run(copy_a)
            copy_b.vars["marker"] = "b"
            with pytest.raises(ConcurrentUpdateError):
                store.save_run(copy_b)
    finally:
        if slug:
            with session_scope() as session:
                AgentService(session).delete_agent(slug)
