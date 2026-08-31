# Skills Spec — v0.1 Cheatsheet

Source: `docs/SKILLS_SPEC_v0.1.md`  
Canvas notation: `docs/FSM_CANVAS_STYLE.md`

## Definition

Skill = managed process for a class of tasks. One FSM per skill in v0.1.

```yaml
id: process_foreman_request
version: "1.0.0"
description: "Process foreman purchase request"
initial: new

params:
  - name: request_id
    type: string
    required: true

states:
  new:
    on:
      request.started:
        actions: [ingest_channel_message]
        to: analyzing

  analyzing:
    on:
      action.parse_request.completed:
        - guard: "result.missing_fields.length == 0"
          to: ready_for_review
        - guard: "result.missing_fields.length > 0"
          actions: [clarify_with_foreman]
          to: waiting_for_foreman

  waiting_for_foreman:
    on_enter: [clarify_with_foreman]
    on:
      channel.message.received:
        actions: [parse_foreman_response]
        to: analyzing

  completed:
    final: true
```

## FSM handler shape

```yaml
on:
  <event_type>:
    - guard: "<expression>"      # optional
      actions: [<action_id>, ...] # optional
      to: <state_id>              # optional
```

Multiple handlers for one event — evaluated in order; must be deterministic.

## Guards

Safe expression engine only. Supported contexts:

```text
result.*    — last action result
event.*     — triggering event fields
payload.*   — event payload shorthand
vars.*      — skill run variables
```

Operators: `==`, `!=`, `>=`, `<=`, `>`, `<`, `.length`

## Event vs Action Result

| Kind | Example | Meaning |
|------|---------|---------|
| Domain event | `channel.message.received`, `human.request.approved` | External fact |
| Action completion | `action.parse_request.completed` | Runtime synthesizes after recipe; `result.*` in guards |

Pattern for action completion: `action.<action_id>.completed`. Do not use bare `<action_id>.completed`.

Both can trigger FSM transitions; don't conflate them.

## Skill Run

- **params** — inputs at start (immutable intent)
- **vars** — runtime variables (mutable during run)
- Lifecycle: `CREATED → RUNNING → WAITING → … → COMPLETED | FAILED | CANCELLED`
- Waiting/suspend = Skill Run concern, not Action

## Correlation

Skill run stores correlation ids (`conversation_id`, `request_id`, `skill_run_id`) synced with event envelope.

## Backend

- Model: `backend/domain/skill.py`
- FSM: `backend/runtime/fsm_engine.py`
- Runner: `backend/runtime/skill_runner.py`
- Guards: `backend/runtime/guards.py`
- Validation: `backend/definition/validation/validate_skill.py`
- Tests: `backend/tests/test_skills_spec.py`

## Frontend

- Types: `frontend/src/features/skills/types/skill.ts`, `fsm.ts`
- Canvas: `frontend/src/features/skills/components/FsmCanvas.vue`
- Inspector: `frontend/src/features/skills/components/SkillInspector.vue`
- Validation: `frontend/src/features/skills/utils/validateSkill.ts`
- YAML: `frontend/src/features/skills/utils/skillYaml.ts`
