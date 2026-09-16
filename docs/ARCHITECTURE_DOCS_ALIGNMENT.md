# Architecture ↔ Docs Alignment

> Статус согласования концептуальных документов (`architecture/`) с нормативными спеками (`docs/*_SPEC`).  
> Обновлено: 2026-09-06.

## Document hierarchy

| Layer | Path | Role |
|-------|------|------|
| **Conceptual** | [`architecture/agent_architecture_v1.md`](../architecture/agent_architecture_v1.md), [`architecture/backend_architecture_v1.md`](../architecture/backend_architecture_v1.md) | Мотивация, модель, направление. Не переопределяет спеки. |
| **Interaction** | [`INTERACTION_SPEC_v0.1.md`](./INTERACTION_SPEC_v0.1.md), план: [`INTERACTION_IMPLEMENTATION_PLAN.md`](./INTERACTION_IMPLEMENTATION_PLAN.md), заметки: [`INTERACTION_IMPLEMENTATION_NOTES.md`](./INTERACTION_IMPLEMENTATION_NOTES.md), синтез: [`INTERACTION_NOTES_ARCHITECTURE_REVIEW.md`](./INTERACTION_NOTES_ARCHITECTURE_REVIEW.md), контора: [`INTERACTION_OFFICE_MODEL.md`](./INTERACTION_OFFICE_MODEL.md), бюро: [`INTERACTION_BUREAU_MODEL.md`](./INTERACTION_BUREAU_MODEL.md), мир: [`INTERACTION_WORLD_MODEL.md`](./INTERACTION_WORLD_MODEL.md) | Человек ↔ агент: стол, голос, фокус, диспетчер, 1 разговор → N работ. Канон слоя над Skill Run. Исполнение уже выбранной работы — RUNTIME/SKILLS. |
| **Normative (execution)** | [`docs/*_SPEC_v0.1.md`](./) | Контракты исполнения — source of truth для runtime v0.1. |
| **Constructor overview** | [`SKILLS_CONSTRUCTOR.md`](./SKILLS_CONSTRUCTOR.md) | FSM-холст Skills: states, publish as-is. Геометрия: [`FSM_CANVAS_GEOMETRY.md`](./FSM_CANVAS_GEOMETRY.md). |
| **Archive** | [`archive/`](./archive/) | Снятые спеки (Behavior Graph, Story/нарратив). Не канон. |
| **Implementation status** | [`RUNTIME_IMPLEMENTATION_STATUS.md`](./RUNTIME_IMPLEMENTATION_STATUS.md) | Соответствие кода `RUNTIME_SPEC`. |
| **This tracker** | `ARCHITECTURE_DOCS_ALIGNMENT.md` | Решения по расхождениям docs ↔ docs; roadmap code gaps. |

```text
architecture/  ──references──►  docs/*_SPEC  ──implemented by──►  backend/frontend
                                      │
                                      ├── INTERACTION_SPEC + INTERACTION_IMPLEMENTATION_PLAN
                                      ├── RUNTIME_IMPLEMENTATION_STATUS.md
                                      └── ARCHITECTURE_DOCS_ALIGNMENT.md (this file)
```

---

## Decision log (бывший §29 agent_architecture)

Ответы на вопросы из [`agent_architecture_v1.md` §29](../architecture/agent_architecture_v1.md).

| # | Вопрос | Канонический ответ | Источник |
|---|--------|-------------------|----------|
| 1 | Выбор Skill для Event | Resume waiting-run только если current_state ждёт этот event.type. Иначе новый run / другой скилл. `conversation_id` ≠ владелец FSM. Полный диспетчер классов (amend / мимо) — фазы 4 плана | [INTERACTION_SPEC](./INTERACTION_SPEC_v0.1.md) R4; RUNTIME §15; [план](./INTERACTION_IMPLEMENTATION_PLAN.md); [заметки](./INTERACTION_IMPLEMENTATION_NOTES.md) |
| 2 | Один Event → несколько Skills | Да — несколько независимых Skill Runs | EVENT §21, RUNTIME §22 |
| 3 | Условный Action | Recipe `when` / условные steps | ACTIONS_SPEC |
| 4 | Формат Action Recipe | Структурированный YAML `steps[]` (`tool`, `input`, `when`) | ACTIONS_SPEC |
| 5 | Где LLM decision making | Вне FSM runtime; LLM — Tool в recipe | backend_arch §22, ACTIONS_SPEC |
| 6 | Может ли LLM выбирать Action | Нет на уровне FSM; FSM выбирает action id по event/guard | SKILLS_SPEC, RUNTIME §9–10 |
| 7 | Permissions / human approval | Domain events `human.request.approved` / `.rejected` / `.corrected` | EVENT §34 |
| 8 | Skill Run variables | `vars` на run; Memory — отдельный Tool | SKILLS §15–16, RUNTIME §6 |
| 9 | Версионирование | Immutable publications; run pin `@version` | RUNTIME §4 |
| 10 | Ошибки и retry | Runtime policy (spec); реализация — gap | RUNTIME §25–27, RI |
| 11 | Planner | Вне scope v0.1; отложен | architecture §23 |
| 12 | Memory + Context | Tools в recipe, не FSM state | ACTIONS_SPEC, backend_arch §21–23 |
| 13 | Canvas FSM / Recipe | Реализовано | [`FSM_CANVAS_STYLE.md`](./FSM_CANVAS_STYLE.md) |
| 14 | Tool Plugin API | TOOLS_SDK + instance model | TOOLS_SDK §39 |
| 15 | Builder vs Runtime UI | Definition plane vs execution plane | RUNTIME §3 |

---

## Doc gap matrix

| Тема | Было | Решение | Статус |
|------|------|---------|--------|
| Разговор vs работа vs фокус | `sessionId` / `conversation_id` склеивались с выбором скилла и waiting-run | Resume только если state ждёт event.type. 1 разговор → N run. Lock `conv-skill`. Таблица-диспетчер. Snapshot/presence | ⚠️ фазы 0–5 = control plane, не коллега. Q1/Q3 да; Q4/Q6 нет. [синтез](./INTERACTION_NOTES_ARCHITECTURE_REVIEW.md) |
| Human approval event | `human.approved` в architecture, EVENT §2, SKILLS §17 | Канон: `human.request.approved` (EVENT §34) | ✅ fixed |
| Human review event | `human.request.reviewed` в SKILLS | Заменено на `human.request.approved` / `.rejected` | ✅ fixed |
| Action completion trigger | `parse_request.completed` как отдельный механизм (SKILLS §17, EVENT §2) | Канон: `action.<action_id>.completed` (RUNTIME §14) | ✅ fixed |
| System vs FSM action events | `action.completed` без уточнения (EVENT §32) | Generic = observability; FSM = `action.<id>.completed` | ✅ fixed |
| Action Recipe format | Shorthand YAML в architecture §6 | Иллюстрация; норма = ACTIONS_SPEC `steps[]` | ✅ fixed |
| Tool model | Только «plugin» в architecture | Tool Type (library) + Tool Instance (per agent) | ✅ fixed |
| Command input schemas | Только description в каталоге | `inputSchema` / `outputSchema` per command — [TOOL_FIELD_SCHEMA_v0.1.md](./TOOL_FIELD_SCHEMA_v0.1.md) | ✅ in progress |
| §29 open questions | 15 нерешённых вопросов | Перенесены в Decision log; остались Planner, multi-tenant, observability | ✅ fixed |
| Multi-skill per event | Spec: да; code: один resolve | `route_all` + `find_waiting_runs` | ✅ fixed |
| Execution store | architecture/backend: `action_runs`, `tool_executions` | Tables + stores wired | ✅ fixed |
| Version pinning | RUNTIME §4: pin per run | `runtime_factory` + pinned resume | ✅ fixed |

---

## Code roadmap

Детальная таблица — в [`RUNTIME_IMPLEMENTATION_STATUS.md`](./RUNTIME_IMPLEMENTATION_STATUS.md). Краткий приоритетный список:

| Priority | Тема | Spec | Status |
|----------|------|------|--------|
| **P0** | Version pinning per run | RUNTIME §4 | ✅ `runtime_factory.py` |
| **P1** | ActionRun / ToolExecution entities | RUNTIME §12–13 | ✅ tables + stores |
| **P1** | Multi-skill per event | EVENT §21 | ✅ `route_all` |
| **P1** | Conversation pin ≠ session ownership | INTERACTION / RUNTIME §15 | ✅ event-type match on current_state |
| **P2** | Cancel / retry / timeout | RUNTIME §26–28 | ⚠️ MVP (retry/timeout/needs_human) |
| **P2** | Event naming in code | EVENT §35 | ✅ aligned in prior docs pass |
| **P3** | Scheduler / replay / metrics | RUNTIME §21,34,43 | ⚠️ MVP (`scheduler.py`, replay API) |
| **P3** | Parallel recipe | RUNTIME §24 | ❌ deferred |

---

## Acceptance checklist

- [x] No `human.approved` in `E.V.A./`
- [x] No `human.request.reviewed` without justification
- [x] SKILLS §17 aligned with RUNTIME §14 (`action.<id>.completed`)
- [x] agent_architecture §29 references Decision log
- [x] architecture describes Tool Type / Instance
- [x] This tracker linked from README and cursor skills
