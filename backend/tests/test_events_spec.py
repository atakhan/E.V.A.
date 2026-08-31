from definition.catalog.builtin_events import (
    BUILTIN_EVENT_TYPES,
    channel_message_received,
    channel_message_sent,
    validate_event_envelope,
)
from definition.mappers.event_mapper import event_from_wire, event_to_wire
from domain.events import Event


def test_channel_message_received_envelope():
    event = channel_message_received(
        conversation_id="conv_1",
        text="hello",
        source="telegram",
        message_id="42",
    )
    issues = validate_event_envelope(event)
    assert issues == []
    assert event.type == "channel.message.received"
    assert event.version == "1.0"
    assert event.source == "telegram"
    assert event.id.startswith("evt_")
    assert event.correlation.conversation_id == "conv_1"


def test_event_wire_roundtrip():
    event = channel_message_sent(
        conversation_id="tg:chat:1",
        text="ok",
        source="telegram",
        skill_run_id="run-1",
    )
    wire = event_to_wire(event, agent_slug="foreman", skill_id="process_foreman_request")
    restored, transport = event_from_wire(wire)
    assert restored.type == event.type
    assert restored.id == event.id
    assert restored.correlation.skill_run_id == "run-1"
    assert transport["agentSlug"] == "foreman"
    assert transport["skillId"] == "process_foreman_request"


def test_legacy_wire_format_is_normalized():
    legacy = {
        "type": "channel.message.received",
        "agentSlug": "foreman",
        "skillId": "process_foreman_request",
        "payload": {"conversation_id": "tg:1", "text": "hi"},
        "skillRunId": "run-9",
    }
    event, transport = event_from_wire(legacy)
    assert event.type == "channel.message.received"
    assert event.version == "1.0"
    assert event.source == "channel"
    assert event.skill_run_id == "run-9"
    assert event.payload["conversation_id"] == "tg:1"
    assert transport["agentSlug"] == "foreman"


def test_builtin_event_catalog_covers_acceptance_types():
    required = {
        "channel.message.received",
        "channel.message.sent",
        "supplier.reply.received",
        "request.created",
        "request.updated",
        "invoice.received",
        "human.request.approved",
        "human.request.corrected",
        "shipment.updated",
        "timer.elapsed",
    }
    assert required.issubset(set(BUILTIN_EVENT_TYPES))
