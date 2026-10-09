# Implementation — технические решения и особенности реализации

> Уровень: **Код**. То, что нужно знать, чтобы менять систему и не удивляться. Каждый пункт — **Fact** по коду, если не указано иное. Проблемы, требующие исправления, продублированы в [`REVIEW.md`](../REVIEW.md).

## 1. Настройки: «всё или ничего»

`app/config.py` требует наличия **всех** переменных (`_require*`); пустое значение допустимо только для `EVA_CREDENTIALS_KEY`, `EVA_WEBHOOK_BASE`, `EVA_DEFAULT_SKILL_IDS` (они через `_require`, не `_require_nonempty`). Booleans — `1/true/yes` / `0/false/no`; choice — `stub|real`, `warn|strict|off`. `get_settings()` кеширован (`lru_cache`); тесты вызывают `get_settings.cache_clear()`. Введено коммитом `e4093bc` («Require explicit env … instead of silent defaults»).

Следствие: любой новый параметр добавляется в **четыре** места: `config.py`, `backend/.env.example`, `docker-compose.{stage,prod}.yml` (`x-backend-environment`), `infisical/*/eva-backend.env.example`.

## 2. Схема БД без миграций

`init_db()`: `Base.metadata.create_all` + три группы `ALTER TABLE … ADD COLUMN IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` для колонок, добавленных после первых деплоев (`tool_api_logs.skill_run_id/action_id/tool_execution_id`, `agents.archived_at`, `skill_runs.revision/expires_at`). Alembic подключён номинально (`alembic.ini`, `alembic/env.py` с одной docstring), ревизий нет. Изменение/удаление колонок и типов этим механизмом невозможно.

## 3. Документ агента — единый JSON

Skills/Actions/Tool instances хранятся как один `body` (JSONB) в `agent_drafts` и копируются в `agent_publications`. Нет внешних ключей между Skill и Action — целостность обеспечивается только валидацией перед publish. Runtime каждый раз разбирает `body` публикации в доменные модели (`skill_from_document`, `normalize_action_document`) — это дёшево, но означает, что «версия Skill/Action» внутри документа декоративна; реальная версия — версия публикации.

## 4. `vars` как носитель всего состояния run

- Входящие payload-поля, correlation, результаты **всех** шагов всех операций, снимок стола (`_desk`), служебные метки (`_agent_slug`, `_last_event_id`, `_needs_human`, `_skill_params`) живут в одном словаре `SkillRun.vars` → JSONB `skill_runs.vars`.
- Ключи `text`, `last_message`, `conversation_id` перезаписываются каждым событием; остальные — только если отсутствуют (`setdefault`-семантика в `_route_single`). Результаты операций перезаписывают всегда.
- Подчёркивание в начале = служебный ключ; `build_action_input` их отфильтровывает, в `payload` шага они тоже не попадают.
- `params` при сохранении копируются в `vars._skill_params` и восстанавливаются оттуда при чтении.

Практический вывод: имена выходных полей команд (`text`, `parsed`, `structured`, `sent`, `snapshot`) становятся глобальными переменными run; две операции с одинаковыми ключами выхода затирают друг друга.

## 5. Области видимости guard и `when` различаются

См. [`02-domain/algorithms.md` §A1](../02-domain/algorithms.md#a1-язык-guard-условий). В `when` шага корень `vars` указывает на scope `{input, vars, steps, payload}`, поэтому документированная форма `vars.x` не работает; работает `payload.x` (= несистемные vars run) или `vars.vars.x`. В guard перехода `event.*` — это `payload`, не конверт. Исправление требует согласованной правки `ActionExecutor._execute_once` и `build_guard_scope` и обновления примеров в `.cursor/skills/eva-specs/actions.md`.

## 6. Оптимистичная блокировка

`skill_runs.revision`: при обновлении проверяется `row.revision == run.revision`, иначе `ConcurrentUpdateError`; worker ловит её, не делает `XACK` (сообщение остаётся в PEL) и спит 0.2 с. **Inference:** повторная доставка из PEL происходит только при следующем `XREADGROUP … >`? Нет — `>` отдаёт только новые сообщения; сообщения в PEL нужно читать по id `0` или через `XAUTOCLAIM`, чего в коде нет. То есть сообщение, оставшееся в PEL после конфликта, **не будет** переобработано этим процессом до рестарта worker (при старте `ensure_consumer_group` с `id="0"` не влияет на уже существующую группу). Помечено в REVIEW как **Unknown/риск** — требует проверки на живом Redis.

## 7. Дедупликация и порядок побочных эффектов

`is_event_processed` проверяется **до** обработки, `mark_event_processed` — **после** `route_all`. Падение между (например, после отправки в Telegram, но до записи) приведёт к повтору побочного эффекта при редоставке. Множество `eva:processed_events` без TTL.

## 8. Два оркестратора

- `runtime/event_router.py` (`EventRouter`) — in-memory ранняя версия: один Skill, резолв по `conversation_id`, без диспетчера, без persist-stores. Используется демо `scenarios/foreman_request.py` и `POST /api/runtime/demo`, тестом `test_foreman_scenario.py`.
- `runtime/runtime_service.py` (`RuntimeService`) — production: мульти-skill через фабрику, диспетчер, stores, лог.

Логика `_sync_correlation`, `_build_run_params/_build_run_vars` **продублирована** в обоих.

## 9. Диспетчер применяется дважды

`runtime_worker._prepared_event` классифицирует акт до блокировки (нужен `skill_run_id` для ключа), затем `RuntimeService.route_all` → `_apply_dispatch` классифицирует **ещё раз** и применяет отмены. Так как на второй проход событие уже может быть переписано/помечено `skill_run_id`, `_is_human_inbound` вернёт `False` → `pass_through`. Это согласованно, но стоит помнить: отмены (`cancel_run_ids`) применяет только второй проход, а первый — только читает.

## 10. Rewrite типа события диспетчером

`_rewrite` создаёт копию события с новым `type` (`ui.request.parse_requested` / `human.request.reviewed`), `payload.entity_ids/entity_id/request_id`, `payload.intent`, `metadata.dispatch.rewritten_from`. Все дальнейшие шаги (поиск скилла, журнал run) видят уже новый тип. Канон «Event = факт» нарушен сознательно как временный прокси (`INTERACTION_NOTES_ARCHITECTURE_REVIEW.md` §7.2).

## 11. Сборка runtime на каждое событие

`build_runtime_service` на каждое сообщение: запрос публикации, парсинг JSON-документа, построение реестра инструментов (включая чтение/расшифровку credentials и создание HTTP-клиентов). Кеша нет. При fan-out на другие Skills (`_service_for_skill`) или другую версию — ещё одна сборка на каждый. **Inference:** при десятках событий в секунду это станет узким местом; на текущих нагрузках приемлемо.

## 12. Инстансы Tools: сборка по типу

`definition_loader._build_tool_for_binding` — `if/elif` по `tool_type` с пятью ветками; типы без ветки возвращают `None` и молча не регистрируются. Режимы `stub` подменяют реализацию целиком (для `polza_ai_llm` — `LlmStubTool` с расширенным списком команд). Инстансу «штампуются» атрибуты `id`, `tool_type`, `credential_id` поверх экземпляра класса (а не через конструктор).

## 13. Валидация входа команды — три режима

`EVA_TOOL_INPUT_VALIDATION`: `strict` (ошибка → `ToolResult(ok=False)`), `warn` (лог + выполнение), `off`. Значения по умолчанию из `inputSchema` применяются во всех режимах. Та же схема питает `SchemaDrivenForm` в UI и валидацию агента (`invalid_step_input`).

## 14. Event: нормализация legacy-форматов

`Event._normalize_legacy` поднимает `skill_run_id`/`skillRunId` с верхнего уровня в `correlation`, копирует correlation-ключи из `payload`; `event_from_wire` подставляет `version/source/timestamp/id`, если их нет, и зеркалит correlation в payload. Благодаря этому старые клиенты (`{type, payload:{conversation_id}}`) продолжают работать. Обратная сторона: одни и те же данные живут в `payload` и `correlation`, и код читает их то оттуда, то отсюда (`payload.get(key) or getattr(event.correlation, key)`).

## 15. Логи инструментов — лучшее усилие

`ToolExecutor._append_log` ловит любые исключения записи лога (не валит операцию). `ToolApiLogService.append` использует ту же сессию, что и runtime, — лог коммитится вместе с run. Единственный писатель лога — executor; инструменты лишь возвращают в `data` поля, которые лог подхватывает (`model`, `usage`, `promptPreview`/`text`). `PolzaAiLlmTool` и `WebClientTool` принимают в конструкторе `agent_id`, `credential_id`, `session`, но Polza их не использует (остаток от прежней схемы логирования внутри Tool).

## 16. Frontend: локальное хранилище + синхронизация

- `agentsStorage.ts`: `agents` — глобальный `ref`; `watch(deep)` пишет в `localStorage` и ставит debounce на `PUT` всего документа каждого агента (`syncAgentsToApi`). Нет оптимистичной блокировки: два открытых окна перезапишут друг друга последним сохранением.
- Если API недоступен при старте — режим `offline`; если API доступен, но пуст, а в `localStorage` есть агенты — миграция `createAgentApi` + `saveAgentApi`.
- Миграции legacy-ключей (`eva.agents.v1`, `eva.applications.*`, `eva.canvases.v1`) и legacy-маршрутов (`/applications/...`, `/:slug/modules/...`, `/:slug/fsm/canvases/...`) сохранены в `router/guards.ts` и `agentsStorage.ts`.

## 17. Frontend: каталог Tools только с сервера

`features/tools/registry/builtinTools.ts` — `builtinTools = []`; всё через `toolCatalogStore` (`GET /api/tools/catalog`, кеш `sessionStorage`). Компоненты, зависящие от каталога, в unit-тестах должны вызывать `setToolCatalogForTests(...)`; `actionSidebarMeta.test.ts` этого не делает → 2 падающих теста в текущем коммите.

## 18. Frontend: FSM-холст

`FsmCanvas.vue` (~1.6k строк) — единственный крупный компонент: SVG, собственная обработка pointer-событий, инструменты, порты (`fromSide/toSide/fromAnchor/toAnchor` хранятся на переходе), маршруты пересчитываются `orthogonalRouter` при любом сдвиге; пользователь не правит сегменты стрелок. Геометрия состояний (`x/y/width/height`) сохраняется в документе и уезжает в публикацию (runtime её игнорирует).

## 19. Снятый эксперимент: Behavior Graph

Коммиты `4d2ae2a` (добавлен) → `4dea5f0` / `e8ffbea` (снят, архив). Остались: backend `definition/behavior/*` (compile/lift/validate/equivalence/materialize) и frontend `features/skills/utils/behavior*.ts`, `types/behavior.ts`, поля `behavior/execution/storyViewport/logicViewport` в `SkillApi`. Единственное живое использование — одноразовый flatten старых черновиков (`flatten_agent_document`, `normalizeSkill`). Тесты `test_behavior_compile.py`, `behaviorCompile.test.ts` поддерживают этот код.

## 20. Сценарии — шаблоны, не seed

`scenarios/*_agent_document.py` строят документы агентов для тестов (`tests/scenario_fixtures.py` публикует их) и ручного импорта; при старте ничего не создаётся. `telegram_webhook_legacy` жёстко ссылается на slug `foreman`.

## 21. Безопасность (как есть)

- API без аутентификации; CORS `allow_origins=["*"]`. Предполагается периметр (`nginx_proxy`, внутренняя сеть) — **Inference**, в коде не задокументировано.
- Единственная авторизация — Bearer `inbound_api_key` на ingress веб-клиента; ключ сравнивается перебором всех `web_client` credentials агента с расшифровкой каждого.
- Credentials шифруются Fernet; при пустом `EVA_CREDENTIALS_KEY` — хранятся как `plain:<json>` с предупреждением (dev).
- Секреты маскируются в логах инструментов (A12), но `tool_calls` в `skill_run_events` и ответе `/runs` содержат сырые `input` шагов (шаблоны уже подставлены) — ключи API туда не попадают, т.к. берутся из credentials, а не из `input`; **Inference**: риск только если пользователь положит секрет в `input` вручную.

## 22. Процессы и масштаб

- Worker однопоточный, синхронный (блокирующие `httpx`, `redis`, SQLAlchemy); один consumer `worker-1`; `XREADGROUP count=10 block=1000`.
- Poller Telegram — отдельный процесс, период 2 с, последовательный обход credentials.
- API — uvicorn (dev `--reload`); все эндпоинты синхронные `def` (кроме `async def` обработчиков webhook/ingress), FastAPI выполняет их в thread pool.
