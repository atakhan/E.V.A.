# Architecture ↔ Docs Alignment

> Статус согласования концептуальных документов (`architecture/`) с нормативными спеками (`docs/*_SPEC`).  
> Обновлено: 2026-08-31.

## Document hierarchy

| Layer | Path | Role |
|-------|------|------|
| **Conceptual** | [`architecture/agent_architecture_v1.md`](../architecture/agent_architecture_v1.md), [`architecture/backend_architecture_v1.md`](../architecture/backend_architecture_v1.md) | Мотивация, модель, направление. Не переопределяет спеки. |
| **Normative** | [`docs/*_SPEC_v0.1.md`](./) | Контракты платформы — source of truth для реализации. |
| **Implementation status** | [`RUNTIME_IMPLEMENTATION_STATUS.md`](./RUNTIME_IMPLEMENTATION_STATUS.md) | Соответствие кода `RUNTIME_SPEC`. |
| **This tracker** | `ARCHITECTURE_DOCS_ALIGNMENT.md` | Решения по расхождениям docs ↔ docs; roadmap code gaps. |

```text
architecture/  ──references──►  docs/*_SPEC  ──implemented by──►  backend/frontend
                                      │
                                      ├── RUNTIME_IMPLEMENTATION_STATUS.md
                                      └── ARCHITECTURE_DOCS_ALIGNMENT.md (this file)
```

---

## Decision log (бывший §29 agent_architecture)

Ответы на вопросы из [`agent_architecture_v1.md` §29](../architecture/agent_architecture_v1.md).

| # | Вопрос | Канонический ответ | Источник |
|---|--------|-------------------|----------|
| 1 | Выбор Skill для Event | Routing по `agent_publication` + correlation; новый Skill Run при отсутствии match | RUNTIME §15, EVENT §21 |
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
