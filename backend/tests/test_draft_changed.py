import copy
from types import SimpleNamespace

import pytest

from definition.services.agent_service import AgentService, changed_runtime_parts
from scenarios.letter_agent_document import build_letter_agent_document

LATER = "2030-01-01T00:00:00+00:00"


def _service(monkeypatch, *, draft: dict | None, published: dict | None) -> AgentService:
    service = AgentService(session=None)
    monkeypatch.setattr(service, "get_agent_by_slug", lambda slug: draft)
    monkeypatch.setattr(
        service,
        "get_latest_publication",
        lambda slug: None if published is None else SimpleNamespace(body=published),
    )
    return service


def test_editor_layout_timestamps_and_world_are_not_draft_changes():
    published = build_letter_agent_document()
    draft = copy.deepcopy(published)
    draft["updatedAt"] = LATER
    draft["constructor"] = {"nodes": [{"id": "node-1", "skillId": "compose_letter", "x": 40, "y": 80}]}
    draft["world"] = {"addresses": [{"id": "sous", "toolId": "web_client", "name": "СОУС"}]}
    skill = draft["skills"][0]
    skill["updatedAt"] = LATER
    skill["viewport"] = {"panX": 120, "panY": -40, "zoom": 0.8}
    for state in skill["states"]:
        state["x"] += 300
        state["y"] += 50
        for transition in state["transitions"]:
            transition.update(fromSide="bottom", toSide="bottom", fromAnchor=0.2, toAnchor=0.8)
    for action in draft["actions"]:
        action["updatedAt"] = LATER
        for step in action["recipe"]:
            step["when"] = ""

    assert changed_runtime_parts(draft, published) == []


@pytest.mark.parametrize(
    ("edit", "part"),
    [
        pytest.param(lambda doc: doc["actions"][0]["recipe"][1].update(command="run"), "actions", id="recipe-step"),
        pytest.param(
            lambda doc: doc["skills"][0]["states"][0]["transitions"][0].update(event="ui.request.other"),
            "skills",
            id="transition-event",
        ),
        pytest.param(
            lambda doc: doc["skills"][0]["states"][1]["onEnter"].append("defer_letter"), "skills", id="on-enter"
        ),
        pytest.param(lambda doc: doc["tools"][1].update(enabled=False), "tools", id="tool-instance"),
        pytest.param(lambda doc: doc.update(defaultSkillId=None), "defaultSkillId", id="default-skill"),
    ],
)
def test_what_runtime_reads_is_a_draft_change(edit, part):
    published = build_letter_agent_document()
    draft = copy.deepcopy(published)
    edit(draft)

    assert changed_runtime_parts(draft, published) == [part]


def test_unreadable_draft_part_counts_as_changed():
    published = build_letter_agent_document()
    draft = copy.deepcopy(published)
    del draft["skills"][0]["states"][0]["id"]

    assert changed_runtime_parts(draft, published) == ["skills"]


def test_draft_changes_are_none_before_first_publication(monkeypatch):
    service = _service(monkeypatch, draft=build_letter_agent_document(), published=None)

    assert service.draft_changes("sous-letter") is None


def test_draft_changes_compare_draft_with_latest_publication(monkeypatch):
    published = build_letter_agent_document()
    draft = copy.deepcopy(published)
    assert _service(monkeypatch, draft=draft, published=published).draft_changes("sous-letter") == []

    draft["actions"][0]["recipe"].pop()
    assert _service(monkeypatch, draft=draft, published=published).draft_changes("sous-letter") == ["actions"]
