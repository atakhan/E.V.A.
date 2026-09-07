from __future__ import annotations

from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from runtime.definition_loader import load_runtime_catalog
from runtime.desk import overlay_entity_from_desk
from runtime.dispatcher import DispatchClass, classify_act
from runtime.runtime_service import RuntimeContext, RuntimeService
from runtime.stores.skill_run_store import InMemoryStore
from tools.registry import ToolRegistry


def _two_skill_body() -> dict:
    return {
        "skills": [
            {
                "id": "razgovor",
                "initial": "IDLE",
                "states": [
                    {
                        "id": "IDLE",
                        "final": False,
                        "transitions": [
                            {"event": "channel.message.received", "actions": [], "to": "IDLE"},
                        ],
                    }
                ],
            },
            {
                "id": "process_supplier_request",
                "initial": "READY",
                "states": [
                    {
                        "id": "READY",
                        "final": False,
                        "transitions": [
                            {"event": "ui.request.parse_requested", "actions": [], "to": "READY"},
                            {"event": "human.request.reviewed", "actions": [], "to": "READY"},
                        ],
                    }
                ],
            },
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
            agent_slug="test-agent",
        )
    )


def _chat(conversation_id: str, text: str, **payload) -> Event:
    return Event(
        type="channel.message.received",
        payload={"conversation_id": conversation_id, "text": text, **payload},
    )


def test_parse_phrase_with_focus_starts_work_not_chat():
    body = _two_skill_body()
    store = InMemoryStore()
    chat = _service("razgovor", store, body)
    conversation_id = "web:desk:d1"
    first = chat.route_all(_chat(conversation_id, "привет"))
    chat_id = first[0].run.id

    results = chat.route_all(
        _chat(
            conversation_id,
            "разбери это",
            focus={"view": "requests", "openEntityId": "REQ-17", "selectedEntityIds": ["REQ-17"]},
        )
    )
    assert len(results) == 1
    assert results[0].run.skill_id == "process_supplier_request"
    assert results[0].run.vars.get("entity_id") == "REQ-17"
    stored_chat = store.runs[chat_id]
    assert stored_chat.status == SkillRunStatus.waiting
    assert stored_chat.error is None


def test_side_question_does_not_cancel_parse():
    body = _two_skill_body()
    store = InMemoryStore()
    service = _service("razgovor", store, body)
    conversation_id = "web:desk:d2"
    service.route_all(_chat(conversation_id, "привет"))
    parse = service.route_all(
        Event(
            type="ui.request.parse_requested",
            payload={"conversation_id": conversation_id, "request_id": "REQ-1", "text": "цемент"},
        )
    )[0].run
    second = service.route_all(_chat(conversation_id, "кто по арматуре?"))
    assert second[0].run.skill_id == "razgovor"
    assert store.runs[parse.id].status == SkillRunStatus.waiting
    assert store.runs[parse.id].error is None


def test_stop_cancels_work_and_keeps_chat():
    body = _two_skill_body()
    store = InMemoryStore()
    service = _service("razgovor", store, body)
    conversation_id = "web:desk:d3"
    parse_id = service.route_all(
        Event(
            type="ui.request.parse_requested",
            payload={"conversation_id": conversation_id, "request_id": "REQ-1", "text": "цемент"},
        )
    )[0].run.id
    results = service.route_all(_chat(conversation_id, "стоп"))
    assert store.runs[parse_id].status == SkillRunStatus.cancelled
    assert results[0].run.skill_id == "razgovor"


def test_amend_cancels_and_starts_narrowed_parse():
    body = _two_skill_body()
    store = InMemoryStore()
    service = _service("razgovor", store, body)
    conversation_id = "web:desk:d4"
    old_id = service.route_all(
        Event(
            type="ui.request.parse_requested",
            payload={"conversation_id": conversation_id, "request_id": "REQ-OLD", "entity_ids": ["REQ-OLD"]},
        )
    )[0].run.id
    results = service.route_all(
        _chat(
            conversation_id,
            "сначала Север",
            focus={"view": "requests", "openEntityId": "REQ-N", "selectedEntityIds": ["REQ-N"]},
        )
    )
    assert store.runs[old_id].status == SkillRunStatus.cancelled
    assert results[0].run.skill_id == "process_supplier_request"
    assert results[0].run.id != old_id
    assert results[0].run.vars.get("entity_id") == "REQ-N"


def test_yes_resumes_waiting_review():
    body = _two_skill_body()
    store = InMemoryStore()
    service = _service("process_supplier_request", store, body)
    conversation_id = "web:desk:d5"
    run_id = service.route_all(
        Event(
            type="ui.request.parse_requested",
            payload={"conversation_id": conversation_id, "request_id": "REQ-1"},
        )
    )[0].run.id
    second = service.route_all(_chat(conversation_id, "да", request_id="REQ-1", entity_ids=["REQ-1"]))
    assert second[0].run.id == run_id
    assert second[0].run.skill_id == "process_supplier_request"


def test_parse_this_without_focus_is_underspecified_chat():
    body = _two_skill_body()
    store = InMemoryStore()
    decision = classify_act(_chat("web:desk:d6", "разбери это"), store, body)
    assert decision.kind == DispatchClass.underspecified
    assert decision.skill_id == "razgovor"


def test_overlay_entity_from_desk_copies_quantity():
    run = SkillRun(
        skill_id="razgovor",
        current_state="IDLE",
        status=SkillRunStatus.waiting,
        vars={"request_id": "REQ-17"},
    )
    overlay_entity_from_desk(
        run,
        {"requests": [{"id": "REQ-17", "quantity": 50, "unit": "мешки", "title": "цемент"}]},
    )
    assert run.vars["quantity"] == 50
    assert run.vars["unit"] == "мешки"
