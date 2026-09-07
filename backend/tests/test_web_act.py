from __future__ import annotations

from app.api.channels.web_act import normalize_web_act
from app.api.channels.event_ingress import enqueue_channel_event
from domain.events import Event


def test_normalize_maps_actor_to_user_id_and_keeps_focus_out_of_actor_field():
    payload, metadata = normalize_web_act(
        {"conversation_id": "web:desk:1", "text": "это"},
        actor_id="user_42",
        focus={"view": "requests", "open_entity_id": "REQ-17", "selected_entity_ids": ["REQ-17"]},
    )
    assert payload["actor_id"] == "user_42"
    assert payload["user_id"] == "user_42"
    assert payload["focus"]["openEntityId"] == "REQ-17"
    assert payload["focus"]["selectedEntityIds"] == ["REQ-17"]
    assert metadata["focus"] == payload["focus"]
    assert payload["entity_ids"] == ["REQ-17"]
    assert payload["entity_id"] == "REQ-17"


def test_normalize_gesture_keeps_intent_and_entity_ids():
    payload, metadata = normalize_web_act(
        {"conversation_id": "web:desk:1", "request_id": "REQ-17", "text": "цемент"},
        actor_id="user_42",
        intent="parse",
        entity_ids=["REQ-17"],
        focus={"view": "requests", "openEntityId": "REQ-17", "selectedEntityIds": ["REQ-17"]},
    )
    assert payload["intent"] == "parse"
    assert payload["entity_ids"] == ["REQ-17"]
    assert metadata["focus"]["view"] == "requests"


def test_enqueue_puts_focus_in_metadata_and_actor_on_correlation(monkeypatch):
    captured: dict[str, Event] = {}

    def fake_publish(event, **kwargs):
        captured["event"] = event
        return event.id

    monkeypatch.setattr("app.api.channels.event_ingress.publish_event", fake_publish)

    result = enqueue_channel_event(
        agent_slug="test-agent",
        event_type="ui.request.parse_requested",
        skill_id="process_supplier_request",
        payload={
            "conversation_id": "web:desk:1",
            "text": "цемент",
            "request_id": "REQ-17",
            "actor_id": "user_42",
            "intent": "parse",
            "entity_ids": ["REQ-17"],
            "focus": {
                "view": "requests",
                "openEntityId": "REQ-17",
                "selectedEntityIds": ["REQ-17"],
            },
        },
    )
    event = captured["event"]
    assert result["queued"] is True
    assert event.type == "ui.request.parse_requested"
    assert event.correlation.user_id == "user_42"
    assert event.correlation.entity_id == "REQ-17"
    assert event.correlation.request_id == "REQ-17"
    assert event.correlation.conversation_id == "web:desk:1"
    assert event.metadata["focus"]["openEntityId"] == "REQ-17"
    assert event.payload["intent"] == "parse"
    assert event.payload["entity_ids"] == ["REQ-17"]
    assert event.payload["focus"]["view"] == "requests"


def test_enqueue_chat_without_act_fields_still_queues(monkeypatch):
    captured: dict[str, Event] = {}

    def fake_publish(event, **kwargs):
        captured["event"] = event
        return event.id

    monkeypatch.setattr("app.api.channels.event_ingress.publish_event", fake_publish)

    enqueue_channel_event(
        agent_slug="test-agent",
        payload={"conversation_id": "web:desk:1", "text": "привет"},
    )
    event = captured["event"]
    assert event.type == "channel.message.received"
    assert event.payload["text"] == "привет"
    assert event.correlation.user_id is None
    assert "focus" not in event.metadata
