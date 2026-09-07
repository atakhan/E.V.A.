from __future__ import annotations

from domain.agent import SkillRun, SkillRunStatus
from domain.events import Event
from runtime.definition_loader import load_runtime_catalog
from runtime.event_lock import event_lock_key
from runtime.runtime_service import RuntimeContext, RuntimeService
from runtime.skill_routing import matching_waiting_run, run_accepts_event, waiting_runs_matching_event
from runtime.stores.skill_run_store import InMemoryStore, store_find_waiting_runs, store_save_run
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
                            {
                                "event": "channel.message.received",
                                "actions": [],
                                "to": "IDLE",
                            }
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
                            {
                                "event": "ui.request.parse_requested",
                                "actions": [],
                                "to": "READY",
                            },
                            {
                                "event": "human.request.reviewed",
                                "actions": [],
                                "to": "READY",
                            },
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


def _chat_event(conversation_id: str, text: str = "привет") -> Event:
    return Event(
        type="channel.message.received",
        payload={"conversation_id": conversation_id, "text": text},
    )


def _parse_event(conversation_id: str, request_id: str = "REQ-1") -> Event:
    return Event(
        type="ui.request.parse_requested",
        payload={"conversation_id": conversation_id, "request_id": request_id, "text": "цемент"},
    )


def test_waiting_chat_does_not_match_parse_event():
    body = _two_skill_body()
    chat_run = SkillRun(skill_id="razgovor", current_state="IDLE", status=SkillRunStatus.waiting)
    matched = waiting_runs_matching_event([chat_run], "ui.request.parse_requested", body)
    assert matched == []
    assert run_accepts_event(chat_run, "channel.message.received", body) is True


def test_waiting_parse_does_not_match_chat_event():
    body = _two_skill_body()
    parse_run = SkillRun(
        skill_id="process_supplier_request",
        current_state="READY",
        status=SkillRunStatus.waiting,
    )
    matched = waiting_runs_matching_event([parse_run], "channel.message.received", body)
    assert matched == []
    assert run_accepts_event(parse_run, "ui.request.parse_requested", body) is True


def test_chat_then_parse_starts_work_skill_and_keeps_chat_waiting():
    body = _two_skill_body()
    store = InMemoryStore()
    chat = _service("razgovor", store, body)
    conversation_id = "web:desk:1"

    first = chat.route_all(_chat_event(conversation_id))
    assert len(first) == 1
    chat_run = first[0].run
    assert chat_run.skill_id == "razgovor"
    assert chat_run.status == SkillRunStatus.waiting
    assert chat_run.current_state == "IDLE"
    chat_last = chat_run.vars.get("last_message")

    second = chat.route_all(_parse_event(conversation_id))
    assert len(second) == 1
    work = second[0].run
    assert work.skill_id == "process_supplier_request"
    assert work.id != chat_run.id
    assert work.status == SkillRunStatus.waiting
    assert work.current_state == "READY"

    stored_chat = store.runs[chat_run.id]
    assert stored_chat.status == SkillRunStatus.waiting
    assert stored_chat.error is None
    assert stored_chat.vars.get("last_message") == chat_last


def test_parse_then_chat_starts_conversation_and_keeps_parse_waiting():
    body = _two_skill_body()
    store = InMemoryStore()
    parse = _service("process_supplier_request", store, body)
    conversation_id = "web:desk:2"

    first = parse.route_all(_parse_event(conversation_id))
    assert first[0].run.skill_id == "process_supplier_request"
    parse_id = first[0].run.id

    second = parse.route_all(_chat_event(conversation_id, "кто по арматуре?"))
    assert len(second) == 1
    assert second[0].run.skill_id == "razgovor"
    assert second[0].run.id != parse_id

    stored_parse = store.runs[parse_id]
    assert stored_parse.status == SkillRunStatus.waiting
    assert stored_parse.error is None
    assert stored_parse.skill_id == "process_supplier_request"


def test_unmatched_domain_event_does_not_error_existing_run():
    """Defense: explicit targeting of a run that cannot handle the event."""
    body = _two_skill_body()
    store = InMemoryStore()
    chat = _service("razgovor", store, body)
    conversation_id = "web:desk:4"
    first = chat.route_all(_chat_event(conversation_id))
    run_id = first[0].run.id
    targeted = Event(
        type="ui.request.parse_requested",
        skill_run_id=run_id,
        payload={"conversation_id": conversation_id, "request_id": "REQ-x"},
    )
    results = chat.route_all(targeted)
    assert results[0].run.id == run_id
    stored = store.runs[run_id]
    assert stored.status == SkillRunStatus.waiting
    assert stored.error is None
    assert stored.vars.get("last_message") == "привет"


def test_second_chat_message_resumes_same_razgovor_run():
    body = _two_skill_body()
    store = InMemoryStore()
    chat = _service("razgovor", store, body)
    conversation_id = "web:desk:3"

    first = chat.route_all(_chat_event(conversation_id, "раз"))
    second = chat.route_all(_chat_event(conversation_id, "два"))
    assert first[0].run.id == second[0].run.id
    assert second[0].run.vars.get("last_message") == "два"
    assert second[0].created is False


def test_two_waiting_runs_on_same_conversation_are_both_found():
    body = _two_skill_body()
    store = InMemoryStore()
    chat = _service("razgovor", store, body)
    conversation_id = "web:desk:5"
    chat_id = chat.route_all(_chat_event(conversation_id))[0].run.id
    parse_id = chat.route_all(_parse_event(conversation_id))[0].run.id

    found = store_find_waiting_runs(store, "conversation_id", conversation_id)
    assert {run.id for run in found} == {chat_id, parse_id}
    assert set(store.by_conversation[conversation_id]) == {chat_id, parse_id}
    assert matching_waiting_run(store, _chat_event(conversation_id), body).id == chat_id
    assert matching_waiting_run(store, _parse_event(conversation_id), body).id == parse_id


def test_matching_waiting_run_without_publication_does_not_pin():
    store = InMemoryStore()
    run = SkillRun(
        skill_id="razgovor",
        current_state="IDLE",
        status=SkillRunStatus.waiting,
        vars={"conversation_id": "web:desk:6"},
    )
    store_save_run(store, run)
    assert matching_waiting_run(store, _chat_event("web:desk:6"), None) is None


def test_lock_keys_chat_and_parse_do_not_collide():
    conversation_id = "web:desk:7"
    chat = _chat_event(conversation_id)
    parse = _parse_event(conversation_id)
    chat_key = event_lock_key(chat, skill_id="razgovor")
    parse_key = event_lock_key(parse, skill_id="process_supplier_request")
    assert chat_key == f"conv-skill:{conversation_id}:razgovor"
    assert parse_key == f"conv-skill:{conversation_id}:process_supplier_request"
    assert chat_key != parse_key


def test_lock_key_same_skill_serializes_two_chats():
    conversation_id = "web:desk:8"
    first = _chat_event(conversation_id, "раз")
    second = _chat_event(conversation_id, "два")
    assert event_lock_key(first, skill_id="razgovor") == event_lock_key(second, skill_id="razgovor")


def test_lock_key_inbound_and_completion_same_skill_share_lock():
    conversation_id = "web:desk:9"
    inbound = _chat_event(conversation_id)
    done = Event(
        type="action.draft_reply.completed",
        skill_run_id="run_razgovor",
        payload={"conversation_id": conversation_id},
    )
    assert event_lock_key(inbound, skill_id="razgovor") == event_lock_key(done, skill_id="razgovor")


def test_lock_key_targeted_without_skill_falls_back_to_run():
    done = Event(type="action.draft_reply.completed", skill_run_id="run_only")
    assert event_lock_key(done) == "run:run_only"


def test_lock_key_without_skill_does_not_lock_whole_conversation():
    event = Event(type="channel.message.received", payload={"conversation_id": "web:desk:10"})
    assert event_lock_key(event) == f"event:{event.id}"


def test_parse_event_focus_and_intent_land_in_run_vars():
    body = _two_skill_body()
    store = InMemoryStore()
    parse = _service("process_supplier_request", store, body)
    event = Event(
        type="ui.request.parse_requested",
        payload={
            "conversation_id": "web:desk:11",
            "request_id": "REQ-17",
            "text": "цемент",
            "user_id": "user_42",
            "intent": "parse",
            "entity_ids": ["REQ-17"],
            "focus": {"view": "requests", "openEntityId": "REQ-17"},
        },
    )
    run = parse.route_all(event)[0].run
    assert run.vars["intent"] == "parse"
    assert run.vars["entity_ids"] == ["REQ-17"]
    assert run.vars["focus"]["openEntityId"] == "REQ-17"
    assert run.vars["user_id"] == "user_42"
