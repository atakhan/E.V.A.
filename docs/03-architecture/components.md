# Components — компоненты и их ответственность

> Уровень: **Как устроено**. Для каждого компонента: назначение, ответственность, вход/выход, зависимости, с кем взаимодействует. Имена модулей даны как ориентир; детали кода — в [`04-code/modules.md`](../04-code/modules.md).

## Backend

### C1. HTTP API (`app/`)

- **Назначение.** Единая точка входа для UI, каналов и ручного/тестового управления runtime.
- **Ответственность.** Роутеры FastAPI; bootstrap при старте (создание схемы, посев каталога Tools, очистка эфемерных агентов); строгая загрузка настроек из окружения.
- **Вход.** HTTP JSON (camelCase).
- **Выход.** JSON; события в шину (ingress каналов); синхронные результаты runtime (dev-путь).
- **Зависимости.** `definition` (сервисы), `runtime` (фабрика, stores), `infrastructure` (session, redis).

Группы маршрутов:

| Префикс | Назначение |
|---|---|
| `/api/agents` | CRUD агентов, черновик (`PUT`), validate, publish, publications, archive/unarchive |
| `/api/agents/{slug}/credentials` | список/создание/удаление/verify/set-webhook credentials |
| `/api/agents/{slug}/tools/polza_ai_llm/*` | models, balance, logs для Polza |
| `/api/agents/{slug}/tools/web_client/*` | integration info, logs, generate-inbound-key |
| `/api/agents/{slug}/tool-logs` | лента логов инструментов, stats |
| `/api/tools/catalog` | каталог типов Tools (манифесты) |
| `/api/runtime/*` | runs (создать/стартовать/список/деталь/история/replay/cancel), events, actions/execute, metrics, summary, demo |
| `/api/channels/telegram/{slug}`, `/api/channels/telegram` | webhook Telegram (второй — legacy для агента `foreman`) |
| `/api/channels/web/{slug}/events`, `…/sessions/{id}/outbox` | ingress актов веб-клиента; outbox |
| `/health`, `/api/hello` | проверки |

### C2. Definition services (`definition/`)

- **AgentService** — черновик, валидация, публикация (bump patch), архивация (с отменой активных run), публикации, удаление; flatten остаточного Behavior Graph при каждом чтении/записи документа.
- **CredentialService** — шифрование/расшифровка секретов, verify (Telegram `getMe`, Polza `GET /balance`, Web Client `GET /eva/health`), `setWebhook`.
- **ToolApiLogService** — запись и выборка логов вызовов инструментов, статистика.
- **Validation** (`validate_agent`, `validate_skill`, `validate_tool_command_input`) — правила A7.
- **Mappers** — документ (camelCase JSON) → доменные модели Skill/Action; событие ↔ wire-формат шины.
- **Catalog** — `BUILTIN_TOOLS` (манифесты реальных и stub-типов), `BUILTIN_EVENT_TYPES`, схема полей (`field_schema`: типы, coercion, defaults, validate).
- **Behavior** — компилятор/лифтер снятого эксперимента Behavior Graph; используется только для одноразового сплющивания старых черновиков.

Вход: документы агента, HTTP-модели. Выход: нормализованные документы, отчёты валидации, строки ORM. Зависимости: `domain`, `infrastructure.models`, `runtime.tool_instance_resolver`.

### C3. Runtime core (`runtime/`)

| Компонент | Ответственность | Вход → выход |
|---|---|---|
| **RuntimeFactory** | собрать runtime для (agent, skill, version): загрузить публикацию, построить каталог Skill+Actions, реестр инстансов Tools с credentials, stores | session, slug, skill id, version → RuntimeService |
| **RuntimeService** | оркестратор одного Skill в одной публикации: применить решение диспетчера, найти/создать run-цели (fan-out, другие Skills через фабрику), подготовить vars, снимок стола, вызвать runner, сохранить run и журнал | Event → список результатов (run + трасса) |
| **Dispatcher** (`classify_act`) | классификация человеческого акта (A5); не мутирует хранилище — отмены применяет вызывающий | Event, store, тело публикации → DispatchDecision |
| **Skill routing / resolver** | какие Skills стартуют на событие; какие ждущие run принимают событие; выбор Skill с учётом `skillId`/`defaultSkillId`/env | тело публикации, event type → ids |
| **SkillRunner** | цикл обработки события на run: шаг → completion-события → авто-переходы → финальный статус; перехват исключений в `error` | run, Event → трасса |
| **FSMEngine** | найти переход (event + guard), применить (actions → state → onEnter), собрать результаты операций | state, Event, vars → TransitionResult |
| **ActionExecutor** | исполнить recipe: вход из vars, дедлайн, `when`, шаблоны, разрешение инстанса, retry, статусы Action Run | ActionDefinition, vars → ActionResult |
| **ToolExecutor** | вызвать команду инстанса: defaults + валидация входа по схеме, retry временных ошибок, Tool Execution, лог API | instance id, command, args, context → ToolResult |
| **Tool instance resolver** | нормализация инстансов, A3, карта credential↔instance | тело агента → инстансы |
| **Desk / Presence** | снимок стола в vars; список открытых работ разговора с ярлыками | run/registry; conversation → данные |
| **Correlation lock / Event lock key** | ключ блокировки A6 и Redis-lock | Event → ключ |
| **DLQ / metrics / scheduler** | счётчик попыток и перенос в DLQ; счётчики; таймеры (process_due) | — |
| **Guards / Expression resolver** | язык guard (A1), шаблоны (A2), вход операции (A10) | строки, scope → значения |
| **Stores (protocol)** | абстракция хранилища run: Postgres и in-memory (тесты, demo) | — |

**EventRouter** (`runtime/event_router.py`) — ранняя in-memory версия оркестратора; используется только демо-сценарием `foreman` и тестами. Production-путь — `RuntimeService`.

### C4. Infrastructure (`infrastructure/`)

- **ORM tables** — 11 таблиц (см. `04-code/modules.md`); `Base.metadata.create_all` при старте + ручные `ALTER TABLE … IF NOT EXISTS` для добавленных позже колонок.
- **Session** — один engine (`pool_pre_ping`), `session_scope()` commit/rollback.
- **Stores** — `PostgresSkillRunStore` (save с `revision`, поиск ждущих по correlation, журнал событий run, cancel, list/summary для cockpit), `PostgresActionRunStore`, `PostgresToolExecutionStore`, `WebClientSessionStore` (Redis).
- **Event bus** — `publish_event` (валидация конверта → `XADD`), `ensure_consumer_group`, `is/mark_event_processed`.
- **Crypto** — Fernet для credentials.

### C5. Tools (`tools/`)

- **Контракт.** `Tool.handle(command, args, context) → ToolResult{ok, data, events, error}`; `BaseTool` диспетчеризует в `cmd_<command>`; инстансу при сборке проставляются `id` (instance id), `tool_type`, `credential_id`.
- **Реестр.** `ToolRegistry` — по instance id. Собирается фабрикой из **включённых** инстансов публикации; для типов без реализации инстанс пропускается.
- **Пакеты.** `llm/` (stub), `polza/` (HTTP-клиент + Tool, логирует вызовы), `telegram/` (real + stub), `text/` (строковые операции с regex-валидацией), `web_client/` (config, http, tool). У каждого — `manifest.py` для каталога.
- **Режимы.** `EVA_TELEGRAM_MODE` и `EVA_POLZA_MODE` = `stub|real` подменяют реализацию для dev/тестов.
- **Scaffold.** `python -m tools.scaffold create <name> --commands "a,b"` генерирует пакет; регистрация в каталоге и фабрике — вручную.

### C6. Workers (`workers/`)

- **runtime_worker** — читает поток группой (`XREADGROUP`, consumer `worker-1`, по 10 сообщений, block 1 с); на каждое сообщение: дедуп → предварительная классификация акта (для ключа блокировки) → lock → разрешить runtime (явный run / ждущий run / выбор Skill, пин версии) → `route_all` → mark processed → публикация вложенных событий инструментов → `process_due` таймеров → `XACK`. Ошибка → счётчик попыток → DLQ после N. `ConcurrentUpdateError` → сообщение остаётся в PEL.
- **telegram_poller** — каждые 2 с для каждого Telegram-credential (кроме dev-stub) `getUpdates` с offset в Redis; нормализует update → `channel.message.received` → шина, с `skillId` по A4. При `EVA_TELEGRAM_POLLING=false` спит.

## Frontend

| Feature | Назначение | Ключевые части | Взаимодействует с |
|---|---|---|---|
| **agents** | список агентов (архив), создание/редактирование, Overview с чеклистом готовности и отчётом валидации, publish | `agentsStorage` (store + localStorage + sync), `agentsApi`, `validateAgent`, `useAgentOverview` | `/api/agents/*`, `/health` |
| **skills** | список Skills, FSM-холст (SVG: состояния, ортогональные стрелки, порты, автораскладка), инспектор, валидация, YAML import/export, импорт пакета skills | `FsmCanvas.vue` (1.6k строк), `SkillInspector.vue`, `utils/geometry/*`, `skillYaml.ts`, `validateSkill.ts` | store агентов |
| **actions** | список Actions и редактор: recipe шаги с schema-driven формой входа по каталогу команд, чипы шаблонов | `ActionEditor.vue`, `RecipeStepEditor.vue`, `commandInputSchema.ts`, `actionSidebarMeta.ts` | каталог Tools, store агентов |
| **constructor** | стол агента: адреса слева, каналы внешнего мира, тело агента, навыки справа. Каталог каналов снизу на весь экран. Панели канала, адреса и навыка на всю высоту справа | `ConstructorView.vue`, `InfiniteCanvas.vue`, `useWorldConnections`, `evaluateWorldLink` | черновик агента (`world`, `constructor`, `tools`) |
| **tools** | глобальная библиотека: группа «Внешний мир» и «Инструменты действий»; инстансы агента; редактор инстанса; панели Polza и Web Client; логи | `toolCatalogStore`, `credentialsApi`, `webClientApi`, `toolLogsApi`, `ToolLibraryView.vue`, `WebClientPanel.vue` | `/api/tools/catalog`, `/api/agents/{slug}/credentials`, `/api/agents/{slug}/tools/*`, `/tool-logs` |
| **runtime** | глобальный dashboard (totals, агенты), cockpit агента (фильтры, список run, cancel), деталь run (timeline событий, action runs, tool executions), simulate (publish + тестовое событие + follow-up события) | `runtimeApi`, `useSkillRunList`, `useSkillRunDetail`, `useAgentRuntime`, `RuntimeSimulateView.vue` | `/api/runtime/*`, `/api/agents/{slug}/publications` |
| **workspace** | каркас страницы агента: плавающее меню разделов Конструктор / Overview / Skills / Actions / Tools / Logs / Runtime | `AgentWorkspaceView.vue`, `AgentFloatingMenu.vue`, `config/nav.ts` | router |
| **shared** | AppShell, бренд, `SchemaDrivenForm` (рендер полей `ToolFieldDef`), `fieldSchema.ts` (порт backend `field_schema`), утилиты slug/date/id | — | — |

## Внешние компоненты (окружение)

| Компонент | Роль | Где описан |
|---|---|---|
| `nginx_proxy` (соседний проект workspace) | edge reverse proxy для stage/prod: домены `eva(-stage).tetrakom-crm-miniapp.ru`, маршрутизация `/api/` → backend, `/` → frontend nginx :8080 | [`integrations.md`](./integrations.md), [`05-operations/deployment.md`](../05-operations/deployment.md) |
| Infisical | хранилище секретов; `infisical run` подставляет env в compose | там же |
| `examples/web_client_stub` | эталонная реализация контракта веб-клиента (FastAPI, :8765) | [`integrations.md`](./integrations.md) |
