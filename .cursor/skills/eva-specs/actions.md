# Actions Spec — v0.1 Cheatsheet

Source: `E.V.A./docs/ACTIONS_SPEC_v0.1.md`

## Definition

Action = atomic agent operation. Hides tool details from FSM.

```yaml
id: parse_request
version: "1.0.0"
description: "Parse incoming request"
policy: {}
inputSchema: { type: object, ... }
outputSchema: { type: object, ... }
recipe:
  - id: llm_step
    tool: llm
    command: run_structured
    input:
      text: "{{input.raw_text}}"
    when: "vars.use_llm == true"   # optional step condition
```

## Recipe step fields

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Unique within recipe |
| `tool` | yes | Tool id from agent bindings |
| `command` | yes | Tool command id |
| `input` | no | Command input; supports templates |
| `when` | no | Local step condition (not FSM guard) |

## Templates

```text
{{input.request_id}}
{{vars.conversation_id}}
{{steps.context.result}}
```

## Boundaries

- FSM sees **action id** and **action result** — not internal recipe steps.
- Completion event for FSM: `action.{action_id}.completed`
- Recipe conditions = local technical logic; FSM guards = process logic.
- No action-in-action composition in v0.1 — use Skill FSM instead.
- Long waits (hours/days) belong to **Skill Run**, not Action executor.

## Policy (v0.1)

Optional fields: `timeout`, `retry`, `idempotency`, `permissions`, `humanGate`.

## Backend

- Model: `backend/domain/action.py`
- Executor: `backend/runtime/action_executor.py`
- Resolver: `backend/runtime/expression_resolver.py`
- Mapper: `backend/definition/mappers/action_mapper.py`
- Tests: `backend/tests/test_actions_spec.py`

## Frontend

- Types: `frontend/src/features/actions/types/action.ts`
- Normalize: `frontend/src/features/actions/types/normalize.ts`
- Editor: `frontend/src/features/actions/components/ActionEditor.vue`
