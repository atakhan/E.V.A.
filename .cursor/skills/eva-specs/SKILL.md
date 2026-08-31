---
name: eva-specs
description: >-
  E.V.A. platform specifications (Actions, Skills, Events, Tools). Use when
  implementing or validating runtime behavior, editing specs in E.V.A./docs,
  or aligning backend/frontend with the v0.1 contracts.
---

# E.V.A. Specifications

**Read this skill** when a task touches platform contracts, runtime semantics, or `E.V.A./docs/`.

Full specs (source of truth):

| Spec | Path |
|------|------|
| Actions | `E.V.A./docs/ACTIONS_SPEC_v0.1.md` |
| Skills | `E.V.A./docs/SKILLS_SPEC_v0.1.md` |
| Events | `E.V.A./docs/EVENT_SPEC_v0.1.md` |
| Tools | `E.V.A./docs/TOOLS_SDK_SPEC_v0.1.md` |
| Runtime | `E.V.A./docs/RUNTIME_SPEC_v0.1.md` |

Implementation gap tracker: `E.V.A./docs/RUNTIME_IMPLEMENTATION_STATUS.md`

Architecture ↔ docs alignment: `E.V.A./docs/ARCHITECTURE_DOCS_ALIGNMENT.md`

Condensed references: `.cursor/skills/eva-specs/{actions,skills,events,tools,runtime}.md`

## Platform model

```text
Agent
  ├── Skills (FSM)     — how to solve a class of tasks
  ├── Actions (recipe) — what to do (atomic operation)
  └── Tools (commands) — technical capabilities

Event → FSM → Action → Tool → World → Event
```

Boundaries:

- **Tool** — capability (`telegram.send_message`). No business logic, no FSM control.
- **Action** — operation (`parse_request`). Recipe of tool commands. Hides implementation from FSM.
- **Skill** — process (`process_foreman_request`). FSM with states, events, guards, action ids.
- **Event** — fact (`channel.message.received`). Not a command. FSM decides what to do.

## Code mapping

| Layer | Backend | Frontend |
|-------|---------|----------|
| Actions | `domain/action.py`, `runtime/action_executor.py`, `definition/mappers/action_mapper.py` | `features/actions/` |
| Skills | `domain/skill.py`, `runtime/fsm_engine.py`, `runtime/skill_runner.py`, `runtime/guards.py` | `features/skills/` |
| Events | `domain/events.py`, `definition/mappers/event_mapper.py`, `infrastructure/redis/event_bus.py` | `features/skills/utils/skillEvents.ts` |
| Tools | `tools/`, `tools/registry.py`, `runtime/definition_loader.py` | `features/tools/` |
| Validation | `definition/validation/validate_*.py` | `validateAgent.ts`, `validateSkill.ts` |
| Tests | `tests/test_actions_spec.py`, `test_skills_spec.py`, `test_events_spec.py` | — |

Runtime implementation status: `docs/RUNTIME_IMPLEMENTATION_STATUS.md`

## When to read which reference

| Task | Read |
|------|------|
| Action recipe, templates, policy, completion events | `actions.md` |
| FSM states, guards, params, skill run lifecycle | `skills.md` |
| Event envelope, correlation, naming, routing | `events.md` |
| Tool manifest, commands, credentials, package layout | `tools.md` |
| SkillRun, worker, pinning, retry, execution history | `runtime.md` |

## Cross-cutting rules (v0.1)

1. FSM references **Action ids**, never tool commands directly (`Skill → Action → Tool`).
2. FSM transitions on **domain events** (`channel.message.received`) or **action results** (`action.parse_request.completed`).
3. Recipe steps use `input` + optional `when` — not `args`.
4. Template refs: `{{input.*}}`, `{{vars.*}}`, `{{steps.<id>.result}}`.
5. Guards: safe expression engine — `result.*`, `event.*`, `payload.*`, `vars.*`, comparisons, `.length`.
6. Events use envelope: `id`, `type`, `version`, `source`, `timestamp`, `correlation`, `payload`, `metadata`, `causation_id`.
7. Event names describe facts (`entity.verb`), not commands (`send_message`).

## Verify after spec-aligned changes

```bash
# backend
docker compose run --rm backend pytest tests/ -q

# frontend
cd E.V.A./frontend && npm run build
```
