# Runtime Spec — v0.1 Cheatsheet

Source: `E.V.A./docs/RUNTIME_SPEC_v0.1.md`  
Gap tracker: `E.V.A./docs/RUNTIME_IMPLEMENTATION_STATUS.md`

## Planes

```text
Definition: Agent, Skill, Action, Tool (published, versioned)
Runtime:    SkillRun, ActionRun, ToolExecution, Event
```

## Execution loop

```text
Event → Dispatcher (act class) → waiting run only if current_state handles event.type → else new SkillRun → FSM → Action → Tool
```

Waiting on `conversation_id` must **not** swallow a card button just because the chat skill is waiting for the next message. Resume iff the state's transitions include this event type.

Worker lock: `conv-skill:{conversation}:{skill}` when both are known (inbound and completion of the same skill serialize; chat vs parse do not share a lock). Not the whole conversation.

## SkillRun status (spec)

```text
CREATED → RUNNING → WAITING → RUNNING → COMPLETED
                              ↘ FAILED / CANCELLED
```

**Code today:** `running`, `waiting`, `completed`, `error`, `cancelled` (unused).

## FSM transition label (UML)

```text
event [guard] / action1, action2
```

## Transition apply order (§10)

1. transition.actions  
2. update state  
3. on_enter actions  
4. persist run  

## Runtime API (conceptual)

```text
publish_event(event)
start_skill(skill_id, version, params)
resume_skill(skill_run_id, event)
cancel_skill(skill_run_id)
get_skill_run(skill_run_id)
execute_action(action_id, version, input)
```

## Backend map

| Area | Path |
|------|------|
| Orchestrator | `runtime/runtime_service.py` |
| FSM | `runtime/fsm_engine.py`, `guards.py` |
| Runner | `runtime/skill_runner.py` |
| Actions | `runtime/action_executor.py` |
| Tools | `runtime/tool_executor.py`, `definition_loader.py` |
| Worker | `workers/runtime_worker.py` |
| Bus | `infrastructure/redis/event_bus.py` |
| Persistence | `infrastructure/stores/postgres_skill_run_store.py` |
| HTTP | `app/api/runtime.py` |

## Top gaps (see status doc)

- Version pinning: loader uses latest publication, not run's pinned version  
- No ActionRun / ToolExecution entities  
- No cancel / retry / timeout at runtime level  
- No optimistic locking on SkillRun  
