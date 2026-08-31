# Events Spec — v0.1 Cheatsheet

Source: `docs/EVENT_SPEC_v0.1.md`

## Definition

Event = fact that something happened. Not a command. FSM decides response.

```text
Event → FSM → Action → Tool → World → Event
```

## Event vs Command vs Result

| Type | Example | Says |
|------|---------|------|
| Command | `telegram.send_message` | Do X |
| Event | `channel.message.received` | X happened |
| Result | `action.parse_request.completed` | Operation X finished |

## Envelope (required fields)

```json
{
  "id": "evt_123",
  "type": "channel.message.received",
  "version": "1.0",
  "source": "telegram",
  "timestamp": "2026-08-27T18:00:00Z",
  "correlation": {
    "conversation_id": "conv_123",
    "skill_run_id": "run_991"
  },
  "payload": { },
  "metadata": { },
  "causation_id": "evt_prev"
}
```

- `id` — stable, used for dedup (at-least-once delivery)
- `timestamp` — when event occurred, not when processed
- `correlation` — links events to execution context
- `causation_id` — direct cause chain (≠ correlation)

## Naming

Good: `channel.message.received`, `supplier.reply.received`, `human.request.approved`, `human.request.rejected`

Bad: `new_msg`, `do_the_thing`, `something_happened`, `human.approved`

Pattern: `<domain>.<entity>.<past_tense_verb>`

### Action completion (FSM)

```text
action.<action_id>.completed   # FSM trigger after Action
action.<action_id>.failed      # FSM trigger on failure
action.completed               # system/observability only — not for FSM
```

## Routing

- Event bus delivers to subscribed skill runs / agents
- `agentSlug` / `skillId` are transport routing headers — not part of domain envelope
- Dedup via processed-events set (`eva:processed_events`)

## Backend

- Model: `backend/domain/events.py`
- Mapper: `backend/definition/mappers/event_mapper.py`
- Catalog: `backend/definition/catalog/builtin_events.py`
- Bus: `backend/infrastructure/redis/event_bus.py`
- Ingress: `backend/app/api/channels/event_ingress.py`
- Tests: `backend/tests/test_events_spec.py`

## Frontend

- Types: `frontend/src/features/skills/utils/skillEvents.ts` (`EvaEvent`, `EventCorrelation`)

## Common event types (v0.1)

```text
channel.message.received
channel.message.sent
action.<id>.completed
```
