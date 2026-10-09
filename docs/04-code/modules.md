# Modules — ключевые модули, классы, интерфейсы

> Уровень: **Код**. Карта «механика → где реализована» и публичные интерфейсы, которые нужны, чтобы менять систему. Не каталог всех функций.

## Трассировка: домен → код

| Доменная механика ([`02-domain/mechanics.md`](../02-domain/mechanics.md)) | Backend | Frontend |
|---|---|---|
| M1 Черновик/валидация/публикация | `definition/services/agent_service.py` (`upsert_draft`, `validate_draft`, `publish`, `_bump_patch`), `definition/validation/*`, `definition/behavior/materialize.py` | `features/agents/services/agentsStorage.ts`, `agentsApi.ts`, `utils/validateAgent.ts`, `features/skills/utils/validateSkill.ts`, `composables/useAgentOverview.ts` |
| M2 Пин версии | `runtime/runtime_factory.py` (`resolve_publication`), `workers/runtime_worker.py` (`_pinned_version_for_event`), `SkillRun.skill_version` | — (cockpit показывает `publicationVersion`) |
| M3 Маршрутизация | `runtime/runtime_service.py` (`_resolve_targets`, `_event_targets_run`), `runtime/skill_routing.py`, `runtime/skill_resolver.py` | — |
| M4 Диспетчер | `runtime/dispatcher.py` (`classify_act`), применение: `RuntimeService._apply_dispatch`, `runtime_worker._prepared_event` | — |
| M5 Шаг автомата | `runtime/skill_runner.py` (`handle`, `_step`, `_drain_auto`, `_finalize_status`), `runtime/fsm_engine.py` (`find_transition`, `apply_transition`), `runtime/guards.py` | холст редактирует `states[]`: `features/skills/components/FsmCanvas.vue`, `SkillInspector.vue` |
| M6 Операция/recipe | `runtime/action_executor.py` (`execute`, `_execute_once`), `runtime/expression_resolver.py`, `runtime/tool_executor.py`, `runtime/tool_instance_resolver.py` | `features/actions/components/ActionEditor.vue`, `RecipeStepEditor.vue`, `utils/commandInputSchema.ts`, `features/tools/utils/resolveToolInstance.ts` |
| M7 Ожидание/возобновление | `SkillRunStatus.waiting`, `PostgresSkillRunStore.find_waiting_runs`, `skill_routing.waiting_runs_matching_event` | cockpit: `features/runtime/*` |
| M8 Человек в контуре | `ActionExecutor` (`needs_human`), `app/api/channels/web_act.py`, `runtime/desk.py`, `runtime/presence.py`, `tools/web_client/tool.py` | `features/tools/components/WebClientPanel.vue`, `WebClientSetupGuide.vue` |
| M9 Надёжность | `infrastructure/redis/event_bus.py`, `runtime/correlation_lock.py`, `runtime/event_lock.py`, `runtime/dlq.py`, `PostgresSkillRunStore.save_run` (`revision`), `runtime/exceptions.py` | — |
| M10 Отмена | `PostgresSkillRunStore.cancel_run`, `cancel_active_runs_for_agent`, `PostgresActionRunStore.cancel_active_for_run`, `RuntimeService.cancel_run`, `POST /api/runtime/runs/{id}/cancel` | `features/runtime/components/SkillRunActions.vue` |
| M11 Таймеры | `runtime/scheduler.py`, `TimerScheduleRow` | — |
| M12 Наблюдаемость | `PostgresSkillRunStore.append_event_log/list_event_logs/summarize_*`, `definition/services/tool_api_log_service.py`, `runtime/tool_log_context.py`, `runtime/metrics.py`, `app/api/runtime.py` (`get_run_history`, `replay_run`) | `features/runtime/components/SkillRunTimeline.vue`, `features/tools/views/ToolLogsView.vue`, `ToolLogFeed.vue` |
| M13 Валидация входа команды | `definition/catalog/field_schema.py`, `definition/validation/validate_tool_command_input.py`, `ToolExecutor.execute` (режим из settings) | `shared/schema/fieldSchema.ts`, `SchemaDrivenForm.vue` |
| M14 Каналы | `app/api/channels/*`, `workers/telegram_poller.py`, `tools/telegram/`, `tools/web_client/` | `WebClientPanel.vue` (ingress/outbox) |

## Backend: ключевые классы и функции

### Домен (`domain/`)

```python
class SkillRun(BaseModel):            # agent.py
    id, skill_id, skill_version, current_state, status: SkillRunStatus,
    params, vars, history, error, revision, expires_at
    def record_state(state_id)       # current_state = …, history.append

class SkillDefinition(BaseModel):     # skill.py
    id, name, description, version, initial, params: list[SkillParam], states: list[FsmState]
    def state_map() / get_state(id)
class FsmState: id, on_enter, final, transitions: list[FsmTransition]
class FsmTransition: id, event, guard, actions, to

class ActionDefinition(BaseModel):    # action.py
    id, name, description, version, policy: "auto"|"needs_human", on_failure, retry: dict,
    timeout_ms, input_schema (alias inputSchema), output_schema, recipe: list[ActionRecipeStep]
class ActionRecipeStep: id, tool, command, input: dict, when

class Event(BaseModel):               # events.py
    id, type, version, source, timestamp, correlation: EventCorrelation, payload, metadata,
    causation_id (alias causationId), skill_run_id (alias skillRunId)
    # before-validator: legacy skill_run_id → correlation; correlation-ключи payload → correlation
class ToolResult: ok, data, events: list[Event], error, tool_execution_id
class ActionResult: action_id, ok, data, tool_calls, events, error, action_run_id, needs_human
```

### Runtime — публичные точки входа

```python
# runtime/runtime_factory.py — единственный способ собрать production-runtime
build_runtime_service(session, *, agent_slug, skill_id, publication_version=None) -> RuntimeService
build_runtime_service_for_publication(session, *, agent_slug, skill_id, publication) -> RuntimeService

# runtime/runtime_service.py
@dataclass RuntimeContext(catalog, registry, store, agent_id, agent_slug, publication_version,
                          publication_body, event_log, session, credential_by_instance, agent_body,
                          action_run_store, tool_execution_store)
class RuntimeService:
    route(event) -> RouterResult            # первый результат; RuntimeError если целей нет
    route_all(event) -> list[RouterResult]  # dispatch → targets → _route_single для каждого
    cancel_run(run_id) -> SkillRun | None
    get_run(run_id)

# runtime/dispatcher.py
classify_act(event, store, agent_body) -> DispatchDecision(kind, event, skill_id, resume_run_id, cancel_run_ids, note, follow_with_chat)

# runtime/skill_resolver.py
resolve_skill_for_event(agent_body, event_type, *, explicit_skill_id, agent_slug, allow_env_fallback) -> SkillResolution(skill_id, reason, error, ambiguous, deprecated)
resolve_skill_for_agent_slug(session, *, agent_slug, event_type, explicit_skill_id) -> SkillResolution

# runtime/skill_routing.py
find_skills_for_event(agent_body, event_type) -> list[str]        # по initial state
run_accepts_event(run, event_type, agent_body) -> bool             # по current_state
waiting_runs_matching_event(waiting, event_type, agent_body) -> list[SkillRun]
matching_waiting_run(store, event, agent_body) -> SkillRun | None

# runtime/fsm_engine.py
class FSMEngine(skill, actions, action_executor):
    find_transition(state, event, vars) -> FsmTransition | None
    apply_transition(run, transition, event) -> TransitionResult(from_state, to_state, event, actions, tool_calls, emitted_events, action_completions)
AUTO_EVENT = "runtime.continue"; action_completed_event_type(id) -> f"action.{id}.completed"

# runtime/skill_runner.py
class SkillRunner(skill, fsm): handle(run, event) -> SkillRunTrace(skill_run_id, states, transitions, tool_calls, status, error)

# runtime/action_executor.py
class ActionExecutor(tool_executor, *, resolve_tool_ref=None, action_run_store=None):
    execute(action, *, vars, skill_run_id=None) -> ActionResult

# runtime/tool_executor.py
class ToolExecutor(registry, log_context=None, tool_execution_store=None):
    execute(tool_id, command, args, context, *, max_attempts=1) -> ToolResult

# runtime/guards.py / expression_resolver.py
evaluate_guard(guard, *, vars, payload) -> bool ; is_valid_guard_syntax(guard) -> bool
resolve_value(value, scope) -> Any ; build_action_input(vars) -> dict

# runtime/stores/skill_run_store.py
class SkillRunStore(Protocol): get_run, save_run, find_waiting_by_conversation, find_waiting_runs(correlation_key, value), map_conversation
```

### Tools

```python
# tools/base.py
class Tool(Protocol): id: str; handle(command, args, context) -> ToolResult
class BaseTool: id, tool_type, credential_id, commands: tuple[str, ...]; handle → cmd_<command>(args, context)

# tools/registry.py
class ToolRegistry(tools): register(tool), get(id), require(id); with_stubs()

# runtime/definition_loader.py
build_tool_registry(agent_body, *, agent_id, session) -> ToolRegistry   # по включённым инстансам, с учётом *_MODE
load_runtime_catalog(agent_body, skill_id) -> RuntimeCatalog(skill, actions)

# манифест типа (dict) — definition/catalog/builtin_tools.py: BUILTIN_TOOLS, get_tool_definition, get_command_input_schema
# поля — definition/catalog/field_defs.py: field(id, type=, required=, default=, label=, placeholder=…), config_field(...)
```

Контекст, который получает команда: `{"vars", "skill_run_id", "action_id", "action_run_id", "action_input", "steps"}`.

### Definition

```python
class AgentService(session):
    list_agents(include_archived), get_agent_by_slug(slug) -> dict | None, create_agent(name, slug, description),
    upsert_draft(slug, payload), delete_agent, archive_agent, unarchive_agent, validate_draft(slug) -> report,
    publish(slug) -> {ok, version, publicationId}, list_publications, get_latest_publication, get_publication(slug, version)
prune_ephemeral_agents(session); seed_tool_catalog(session)

class CredentialService(session):
    list_credentials(slug, tool_id), create_credential(slug, *, tool_id, name, secret), delete_credential,
    get_secret(agent_id, credential_id) -> dict, verify_credential, set_telegram_webhook

validate_agent(agent: dict) -> {"issues": [...], "errors", "warnings", "infos"}
validate_skill(skill, *, action_ids, href) -> issues
skill_from_document(doc) -> SkillDefinition ; normalize_action_document(doc) -> ActionDefinition
create_domain_event(type, *, source, payload, correlation, skill_run_id, action_run_id, causation_id, metadata) -> Event
event_to_wire(event, *, agent_slug, skill_id) -> dict ; event_from_wire(data) -> (Event, transport)
channel_message_received(...), channel_message_sent(...)   # builtin_events.py
```

### Infrastructure

| Таблица (ORM класс) | Назначение |
|---|---|
| `agents` (`AgentRow`) | slug, name, description, archived_at |
| `agent_drafts` (`AgentDraftRow`) | body JSONB (1:1 с агентом) |
| `agent_publications` (`AgentPublicationRow`) | version, body JSONB, published_at; unique(agent_id, version) |
| `tool_catalog` (`ToolCatalogRow`) | посев манифестов (используется только для посева; API читает `BUILTIN_TOOLS` напрямую) |
| `tool_credentials` (`ToolCredentialRow`) | tool_id, name, secret_encrypted, meta |
| `skill_runs` (`SkillRunRow`) | agent_id/slug, skill_id, publication_version, current_state, status, vars, history, conversation_id, error, revision, expires_at |
| `action_runs` (`ActionRunRow`) | FK skill_runs; status, input/output, current_step, attempt, deadline_at |
| `tool_executions` (`ToolExecutionRow`) | FK action_runs; tool_instance_id, command, input/output, status, duration_ms |
| `timer_schedules` (`TimerScheduleRow`) | FK skill_runs; fire_at, event_type, payload, fired |
| `skill_run_events` (`SkillRunEventRow`) | FK skill_runs; event_type, payload, from/to_state, tool_calls, created |
| `tool_api_logs` (`ToolApiLogRow`) | FK agents; tool_id, command, model, status, request/response_summary, usage, duration_ms, skill_run_id, action_id, tool_execution_id |

### Workers

```python
# workers/runtime_worker.py
process_event_data(raw: dict, *, message_id) -> None   # вся обработка одного сообщения потока
run_worker(poll_ms=1000)                                # бесконечный XREADGROUP-цикл
# workers/telegram_poller.py
poll_once() -> int ; run_poller(interval_sec=2.0)
```

## Frontend: ключевые модули

| Модуль | Экспорт / роль |
|---|---|
| `features/agents/services/agentsStorage.ts` | `agents` (ref), `apiAvailable`, `storageReady`, `agentSaveStatus`, `flushAgentsToApi()`; bootstrap: health → список → миграция local→API; watch deep → localStorage + debounce PUT |
| `features/agents/services/agentsApi.ts` | `fetchAgentsList`, `fetchAgent`, `createAgentApi`, `saveAgentApi`, `deleteAgentApi`, `archiveAgentApi`, `unarchiveAgentApi`, `validateAgentApi`, `publishAgentApi`, `checkApiHealth` |
| `features/agents/utils/validateAgent.ts` | порт `validate_agent` (коды — A7) |
| `features/agents/composables/useAgentOverview.ts` | `readinessItems` (skills/actions/tools/validation/published), `readinessProgress`, publish |
| `features/skills/types/skill.ts`, `fsm.ts` | `Skill`, `FsmState`, `FsmTransition`, `SkillParam`; `normalizeSkill` (legacy canvas + остаточный Behavior Graph → states), `createFsmState/Transition` |
| `features/skills/components/FsmCanvas.vue` | SVG-холст: инструменты select/state/transition, drag/resize, порты, выбор, автораскладка; эмитит изменения `states[]` |
| `features/skills/utils/geometry/*` | `orthogonalRouter.ts` (маршруты), `rects.ts`, `routeGraph.ts`, `placement.ts`, `labels.ts`, `autoLayout.ts`, `validate.ts`, `config.ts` |
| `features/skills/utils/skillYaml.ts` | `skillToYaml` / `skillFromYaml` (собственный сериализатор канона `states/on/on_enter`) |
| `features/skills/utils/skillEvents.ts` | `EvaEvent`, `EventCorrelation` типы + известные события для подсказок |
| `features/actions/types/action.ts`, `normalize.ts` | `ActionDef`, `RecipeStep`; `normalizeAction` (legacy `args` → `input`) |
| `features/actions/utils/commandInputSchema.ts` | схема входа команды из каталога для `RecipeStepEditor` |
| `features/tools/services/toolCatalogStore.ts` | `loadToolCatalog()` (fetch + sessionStorage), `getToolDefinitionFromCatalog`, `setToolCatalogForTests` |
| `features/tools/registry/builtinTools.ts` | `getToolDefinition`, `getToolCommandIds`, `getBuiltinTools`, `formatToolCommand` — поверх каталога (`builtinTools = []`) |
| `features/tools/utils/resolveToolInstance.ts` | порт A3 (`resolveRecipeTool`) |
| `features/tools/services/credentialsApi.ts`, `webClientApi.ts`, `toolLogsApi.ts` | клиенты соответствующих API |
| `features/runtime/services/runtimeApi.ts` | `listSkillRuns`, `getRuntimeSummary`, `getAgentRuntimeSummary`, `getRuntimeMetrics`, `createRuntimeRun`, `postRuntimeEvent`, `getRuntimeRun`, `getSkillRunHistory`, `cancelSkillRun`, `listPublicationsApi` |
| `router/paths.ts` | `RouteNames`, builders (`agentSkillsPath`, `skillPath`, `skillRunDetailPath`, …), `legacyModuleSlugToSection` |
| `shared/schema/fieldSchema.ts`, `SchemaDrivenForm.vue` | порт `field_schema.py`; рендер формы по `ToolFieldDef[]` |

## Где менять, если нужно…

| Задача | Точки изменения |
|---|---|
| Новый тип Tool | `tools/<name>/{manifest,tool,__init__}.py` → `definition/catalog/builtin_tools.py` → `runtime/definition_loader._build_tool_for_binding` (+ credential helper в `tools/credential_resolver.py`, если нужен секрет; verify в `CredentialService`; `_CREDENTIAL_TYPES` в `validate_agent.py`) |
| Новый встроенный тип события | `definition/catalog/builtin_events.py` (`BUILTIN_EVENT_TYPES`, фабрика) → при необходимости `frontend/src/features/skills/utils/skillEvents.ts` |
| Новый оператор/функция guard | `runtime/guards.py` (`_GUARD_RE`, `evaluate_guard`, `build_guard_scope`) → `validate_skill.py` использует `is_valid_guard_syntax`; фронтенд `validateSkill.ts` дублирует проверку синтаксиса |
| Новое правило валидации | `definition/validation/validate_agent.py` или `validate_skill.py` **и** `frontend/.../validateAgent.ts` / `validateSkill.ts` (два порта) |
| Новый класс диспетчера | `runtime/dispatcher.py` (`DispatchClass`, `classify_act`); применение решений — `RuntimeService._apply_dispatch`, `runtime_worker._prepared_event` |
| Новое поле Skill Run | `domain/agent.py` → `infrastructure/models/tables.py` → `PostgresSkillRunStore.save_run/_to_domain` → `app/deps.py` (`ALTER TABLE … IF NOT EXISTS`) |
| Новый маршрут runtime API | `app/api/runtime.py` → `frontend/src/features/runtime/services/runtimeApi.ts` + типы в `types/runtime.ts` |
| Новый раздел в workspace агента | `features/workspace/config/nav.ts` → `router/index.ts` → `router/paths.ts` |
