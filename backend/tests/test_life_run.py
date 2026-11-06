from __future__ import annotations

from definition.system_skills import LIFE, system_skill
from domain.events import Event
from runtime.definition_loader import load_runtime_catalog
from runtime.life import (
    attach_life_parent,
    ensure_life_run_on_service,
    find_active_life_run,
    publication_has_life,
)
from runtime.runtime_service import RuntimeContext, RuntimeService
from runtime.skill_routing import find_skills_for_event
from runtime.stores.skill_run_store import InMemoryStore
from tools.registry import ToolRegistry


def _body_with_life_and_chat() -> dict:
    now = "2026-01-01T00:00:00Z"
    return {
        "skills": [
            system_skill("talk_to_human", now=now),
            system_skill(LIFE, now=now),
        ],
        "actions": [],
    }


def _service(skill_id: str, store: InMemoryStore, body: dict) -> RuntimeService:
    catalog = load_runtime_catalog(body, skill_id)
    return RuntimeService(
        RuntimeContext(
            catalog=catalog,
            registry=ToolRegistry(),
            store=store,
            publication_body=body,
            agent_body=body,
            agent_slug="life-agent",
            agent_id="agent-1",
            publication_version="0.1.0",
        )
    )


def test_life_skill_does_not_match_channel_message():
    body = _body_with_life_and_chat()
    assert LIFE not in find_skills_for_event(body, "channel.message.received")
    assert "talk_to_human" in find_skills_for_event(body, "channel.message.received")


def test_ensure_life_run_is_idempotent():
    body = _body_with_life_and_chat()
    store = InMemoryStore()
    service = _service("talk_to_human", store, body)

    first = ensure_life_run_on_service(service)
    second = ensure_life_run_on_service(service)

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert first.skill_id == LIFE
    assert first.current_state == "alive"
    assert first.status.value == "waiting"
    assert find_active_life_run(store, "life-agent") is not None
    assert sum(1 for run in store.runs.values() if run.skill_id == LIFE) == 1


def test_ensure_life_run_skipped_without_life_skill():
    body = {
        "skills": [
            {
                "id": "talk_to_human",
                "initial": "listening",
                "states": [
                    {
                        "id": "listening",
                        "final": False,
                        "transitions": [
                            {"event": "channel.message.received", "actions": [], "to": "listening"}
                        ],
                    }
                ],
            }
        ],
        "actions": [],
    }
    store = InMemoryStore()
    service = _service("talk_to_human", store, body)
    assert publication_has_life(body) is False
    assert ensure_life_run_on_service(service) is None


def test_episode_run_gets_life_parent():
    body = _body_with_life_and_chat()
    store = InMemoryStore()
    service = _service("talk_to_human", store, body)
    event = Event(
        type="channel.message.received",
        payload={"conversation_id": "c1", "text": "привет"},
    )

    result = service.route(event)

    assert result.created is True
    assert result.run.skill_id == "talk_to_human"
    life = find_active_life_run(store, "life-agent")
    assert life is not None
    assert result.run.vars.get("_life_run_id") == life.id
    assert result.run.params.get("parent_run_id") == life.id


def test_attach_life_parent_skips_life_run_itself():
    from domain.agent import SkillRun

    life = SkillRun(skill_id=LIFE, current_state="alive")
    episode = SkillRun(skill_id=LIFE, current_state="alive")
    attach_life_parent(episode, life)
    assert "parent_run_id" not in episode.params
    assert "_life_run_id" not in episode.vars
