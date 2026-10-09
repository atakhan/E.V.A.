# REVIEW — обнаруженные проблемы и расхождения

> Зафиксировано при исследовании проекта 2026-10-08 (коммит `59535b7` + незакоммиченное переименование `docs/ → docs_old/`). **Ничего из перечисленного не исправлялось** — документация описывает существующее состояние. Категории: **Fact** — подтверждено кодом/прогоном; **Inference** — следует из нескольких фактов; **Unknown** — информации недостаточно; **TODO** — требует решения.
>
> Приоритет (субъективная оценка влияния): 🔴 ломает/вводит в заблуждение сейчас · 🟡 риск или долг · ⚪ гигиена.

## 1. Документация ↔ код

| # | Проблема | Где | Тип |
|---|---|---|---|
| 1.1 🔴 | `README.md` ссылается на `docs/*_SPEC_v0.1.md`, `docs/SKILLS_CONSTRUCTOR.md`, `docs/INTERACTION_*`, `docs/RUNTIME_IMPLEMENTATION_STATUS.md`, `docs/ARCHITECTURE_DOCS_ALIGNMENT.md`, `docs/archive/` — после переименования в `docs_old/` все ссылки битые | `README.md` таблица «Документация» | Fact |
| 1.2 🔴 | `.cursor/skills/eva-specs/*.md`, `eva-backend/SKILL.md`, `.cursor/rules/eva-*.mdc`, `architecture/*.md` ссылаются на `docs/…` (спеки) — те же битые пути; `eva-docs-spec.mdc` имеет glob `E.V.A./docs/**/*.md` и будет применяться к новой документации, требуя «согласованности спек» | `.cursor/`, `architecture/` | Fact |
| 1.3 🔴 | Пример `when: "vars.use_llm == true"` в шпаргалке не работает: в `when` корень `vars` — scope шага, нужно `payload.use_llm` или `vars.vars.use_llm` (проверено прогоном) | `.cursor/skills/eva-specs/actions.md`; `runtime/action_executor.py` `_execute_once` + `runtime/guards.build_guard_scope` | Fact |
| 1.4 🟡 | В guard `event.*` — это `payload`, а не конверт (`event.type`/`event.source` недоступны); спеки описывают `event.*` как «triggering event fields» | `runtime/guards.py`; SKILLS cheatsheet | Fact |
| 1.5 🟡 | Спека/alignment объявили `human.request.reviewed` заменённым на `human.request.approved/rejected`; код диспетчера и сценарий `supplier` используют именно `human.request.reviewed` (с `payload.decision`), а каталог содержит `approved`/`corrected` и не содержит `rejected`/`reviewed` | `runtime/dispatcher.py` `REVIEW_EVENT`, `scenarios/supplier_agent_document.py`, `definition/catalog/builtin_events.py`, `docs_old/ARCHITECTURE_DOCS_ALIGNMENT.md` | Fact |
| 1.6 🟡 | Статусы SkillRun: спека `CREATED/RUNNING/WAITING/COMPLETED/FAILED/CANCELLED`, код `running/waiting/completed/cancelled/error` (нет `created`, `failed`→`error`); cheatsheet `runtime.md` помечает `cancelled` как «unused», хотя cancel реализован (API, диспетчер, архивация) | `domain/agent.py`, `docs_old/RUNTIME_SPEC_v0.1.md` §7, `.cursor/skills/eva-specs/runtime.md` | Fact |
| 1.7 🟡 | Scaffold: cheatsheet даёт `python -m tools.scaffold create <name> …`; CLI не имеет подкоманды `create` (позиционный `name`) | `.cursor/skills/eva-specs/tools.md`, `tools/scaffold.py` | Fact |
| 1.8 🟡 | README: Infisical папки `/eva-postgres`, `/eva-redis`, `/eva-backend`; Makefile: `/eva-postgres`, `/backend-environmet` (опечатка; `/eva-redis` удалён коммитом `2b53e41`); шаблоны в `infisical/*/` названы `eva-*` | `README.md`, `Makefile`, `infisical/` | Fact |
| 1.9 🟡 | README предлагает `make stage-secrets-upload` / `make prod-secrets-upload` — целей нет (см. 4.1) | `README.md` | Fact |
| 1.10 ⚪ | `eva-frontend/SKILL.md` перечисляет features `agents, skills, actions, tools, workspace` — отсутствует `runtime/` (крупная фича cockpit) | `.cursor/skills/eva-frontend/SKILL.md` | Fact |
| 1.11 ⚪ | `RUNTIME_IMPLEMENTATION_STATUS.md` (2026-09-06) оценивает «~88 %», но помечает scheduler/replay как MVP; фактически таймер нельзя создать из конструктора (см. 3.3) — формулировка «Scheduler ⚠️ MVP» завышена | `docs_old/RUNTIME_IMPLEMENTATION_STATUS.md` | Inference |
| 1.12 ⚪ | `docs_old/` не упомянут нигде, кроме новой документации; архив `docs_old/archive/README.md` ссылается на `../SKILLS_CONSTRUCTOR.md` и т.п. относительными путями — внутри `docs_old/` они валидны | — | Fact |

## 2. Неясные места и противоречия в коде

| # | Проблема | Где | Тип |
|---|---|---|---|
| 2.1 🟡 | Rewrite типа события диспетчером (`channel.message.received` → `ui.request.parse_requested` / `human.request.reviewed`) нарушает канон «Event = факт»; признано в review как главный онтологический долг, сроков нет | `runtime/dispatcher.py` `_rewrite`; `docs_old/INTERACTION_NOTES_ARCHITECTURE_REVIEW.md` §7.2, §15 | Fact |
| 2.2 🟡 | Диспетчер применяется дважды на событие (worker `_prepared_event` и `RuntimeService._apply_dispatch`); результат согласован только потому, что второй проход видит уже обработанное событие как не-человеческое | `workers/runtime_worker.py`, `runtime/runtime_service.py` | Fact |
| 2.3 🟡 | `params` объявлены как неизменяемое намерение, но `_sync_correlation` перезаписывает их на каждом событии; `required` у params не проверяется при старте run | `runtime/runtime_service.py`, `definition/mappers/skill_mapper.py` | Fact |
| 2.4 🟡 | Результаты всех шагов всех Actions пишутся в общий `vars` без неймспейсов; одинаковые ключи выхода (`text`, `ok`, `sent`) затирают друг друга | `runtime/action_executor.py` `_execute_once` | Fact |
| 2.5 🟡 | `inputSchema`/`outputSchema` Action хранятся, но не применяются (вход строится из `vars`) | `runtime/expression_resolver.build_action_input` | Fact |
| 2.6 🟡 | `retry.max_attempts` одного Action используется и как число попыток Action, и как число попыток каждой команды → до N² вызовов | `runtime/action_executor.py` | Fact |
| 2.7 ⚪ | `build_guard_scope` содержит shorthand `needs_clarification` (legacy демо foreman) в общем движке guard | `runtime/guards.py` | Fact |
| 2.8 ⚪ | `_drain_auto` / `runtime.continue` — legacy авто-переходы (пустой `event`) остаются в движке; валидация предупреждает `empty_event`, но исполнение их принимает | `runtime/skill_runner.py`, `runtime/fsm_engine._event_matches` | Fact |
| 2.9 ⚪ | Дублирование `_sync_correlation`, `_build_run_params`, `_build_run_vars` в `EventRouter` и `RuntimeService` | `runtime/event_router.py`, `runtime/runtime_service.py` | Fact |
| 2.10 ⚪ | Слои нарушены: `definition/validation/validate_agent.py` импортирует `runtime.tool_instance_resolver`; `infrastructure/*` импортирует `app.config` (правило `domain → definition → runtime → app`) | см. файлы | Fact |
| 2.11 ⚪ | `PolzaAiLlmTool` принимает `agent_id`, `credential_id`, `session`, но не использует их (лог пишет executor) | `tools/polza/llm.py` | Fact |
| 2.12 ⚪ | Telegram `parse_mode` объявлен в `configSchema`, но не передаётся в `sendMessage` | `tools/telegram/manifest.py`, `tool.py` | Fact |
| 2.13 ⚪ | Ярлыки присутствия захардкожены по id скиллов (`razgovor`, `chat_with_supplier`, `process_supplier_request`) — бизнес-знание в runtime | `runtime/presence.py` | Fact |
| 2.14 ⚪ | `telegram_webhook_legacy` жёстко маршрутизирует на агента `foreman` | `app/api/channels/telegram.py` | Fact |

## 3. Потенциальные архитектурные/рантайм проблемы

| # | Проблема | Где | Тип |
|---|---|---|---|
| 3.1 🔴 | 7 из 12 типов каталога (`memory`, `context`, `crm`, `catalog`, `web_search`, `files`, `saby`) не имеют реализации: инстанс можно включить и пройти валидацию, но при исполнении шаг упадёт `Tool '<id>' is not registered` (инстанс молча пропущен при сборке реестра) | `definition/catalog/manifests/stubs.py`, `runtime/definition_loader._build_tool_for_binding` | Fact |
| 3.2 🟡 | При `ConcurrentUpdateError` сообщение остаётся в PEL, но worker читает только `>` (новые) и не делает `XAUTOCLAIM`/чтение с `0` → застрявшее сообщение не будет переобработано до ручного вмешательства | `workers/runtime_worker.py` `run_worker` | Inference (требует проверки на живом Redis) |
| 3.3 🟡 | Таймеры: `RuntimeScheduler.schedule` нигде не вызывается (нет DSL/команды); `process_due` вызывается только после обработки другого события и без фильтра по агенту — событие таймера публикуется с `agentSlug`/`skillId` **текущего** события, а не целевого run | `runtime/scheduler.py`, `workers/runtime_worker.py` | Fact |
| 3.4 🟡 | `skill_runs.expires_at` хранится, но нигде не проверяется | `domain/agent.py`, stores | Fact |
| 3.5 🟡 | Дедуп: `mark_event_processed` после побочных эффектов → падение между ними повторит эффект при редоставке; `eva:processed_events` без TTL растёт бесконечно | `workers/runtime_worker.process_event_data`, `infrastructure/redis/event_bus.py` | Fact |
| 3.6 🟡 | `GET /api/runtime/metrics` возвращает счётчики процесса API, тогда как события обрабатывает процесс worker → почти всегда нули | `runtime/metrics.py`, `app/api/runtime.py` | Fact |
| 3.7 🟡 | `build_runtime_service` на каждое событие пересобирает каталог, реестр инструментов и расшифровывает credentials; при fan-out — по разу на каждый Skill/версию; кеша нет | `runtime/runtime_factory.py`, `runtime/runtime_service._service_for_skill` | Fact (производительность — Inference) |
| 3.8 🟡 | Один consumer `worker-1`, синхронный однопоточный worker; масштабирование репликами не предусмотрено (одинаковое имя consumer) | `workers/runtime_worker.py` | Fact |
| 3.9 🟡 | API без аутентификации, CORS `*`; защита предполагается периметром (нигде не задокументировано) | `app/main.py` | Fact / Unknown |
| 3.10 🟡 | Удаление агента не удаляет `skill_runs` (нет FK) — остаются «сироты» с `agent_slug`; `summarize_runtime` их учтёт как агента без публикации | `infrastructure/models/tables.py`, `postgres_skill_run_store.summarize_runtime` | Fact / Inference |
| 3.11 🟡 | Фронтенд синхронизирует весь документ агента с debounce без optimistic-locking: два окна перезапишут друг друга | `features/agents/services/agentsStorage.ts` | Fact |
| 3.12 ⚪ | Crash посреди Action Run: записи остаются `running`, автопродолжения нет | RUNTIME_IMPLEMENTATION_STATUS §44 | Fact |
| 3.13 ⚪ | `replay_run` повторяет побочные эффекты без защит (admin/test) | `app/api/runtime.py` | Fact |
| 3.14 ⚪ | `_verify_inbound_key` расшифровывает все `web_client` credentials агента на каждый запрос ingress | `app/api/channels/web.py` | Fact |

## 4. Операционные дефекты

| # | Проблема | Где | Тип |
|---|---|---|---|
| 4.1 🔴 | Makefile: цели `prod-secrets-check`, `prod-secrets-upload`, `stage-secrets-check`, `stage-secrets-upload` объявлены `.PHONY` и используются как зависимости, но рецептов не имеют (были в `defce8a`/`2b53e41`, исчезли в `e4093bc`/merge `59535b7`) → `make start-prod` не проверяет секреты; `make *-secrets-upload` — no-op («Nothing to be done») | `Makefile` | Fact (проверено `make -n`) |
| 4.2 🟡 | `INFISICAL_PATH_EVA_BACKEND=/backend-environmet` — опечатка и расхождение с шаблонами/README (см. 1.8); `start-stage` не зависит от `stage-secrets-check`, а `build-stage` зависит — несимметрично с prod | `Makefile` | Fact |
| 4.3 🟡 | Alembic — заглушка (`alembic/env.py` одна строка, нет `versions/`), схема — `create_all` + ручные `ALTER`; удаление/изменение колонок невозможно без ручного SQL | `backend/alembic*`, `app/deps.py` | Fact |
| 4.4 ⚪ | `backend/.env`, `backend/.env.stage` присутствуют в рабочем дереве (игнорируются git) — `.env.stage` не используется ни compose, ни Makefile | `backend/` | Fact |
| 4.5 ⚪ | CI/CD отсутствует; линтеры/форматтеры не настроены | — | Fact |
| 4.6 ⚪ | `tool_catalog` таблица засевается при старте, но ничего её не читает (API отдаёт `BUILTIN_TOOLS`) | `definition/services/agent_service.seed_tool_catalog`, `app/api/tools.py` | Fact |

## 5. Тесты

| # | Проблема | Где | Тип |
|---|---|---|---|
| 5.1 🔴 | Frontend: 2 падающих unit-теста в текущем коммите (`actionSidebarMeta.test.ts`: ожидают `ok`/`ambiguous`, получают `unknown`) — каталог Tools в тесте пуст после переноса каталога на сервер; `setToolCatalogForTests` не вызывается | `frontend/src/features/actions/utils/actionSidebarMeta.test.ts` | Fact (прогон vitest) |
| 5.2 🟡 | Нет тестов паритета валидации backend ↔ frontend; сервер знает `missing_credential`/`duplicate_credential`, UI — нет | `validate_agent.py`, `validateAgent.ts` | Fact |
| 5.3 🟡 | Нет тестов `process_event_data` целиком (lock/DLQ/PEL), `scheduler.process_due`, `expires_at`, конкурентности `revision` | `backend/tests/` | Fact |
| 5.4 ⚪ | `conftest.py` фикстуры `ephemeral_agent_slug`, `foreman_agent` зависят от фикстуры `client`, которая определена только в отдельных модулях — фикстуры неприменимы вне них | `backend/tests/conftest.py` | Fact |
| 5.5 ⚪ | Тесты legacy Behavior Graph (`test_behavior_compile.py`, `behaviorCompile.test.ts`) поддерживают снятый эксперимент | — | Fact |

## 6. Мёртвый и legacy-код

| # | Что | Где | Тип |
|---|---|---|---|
| 6.1 | Пустые каталоги `frontend/src/{components/canvas,components/home,composables,data,types,utils,views}` | frontend | Fact |
| 6.2 | `definition/behavior/*` (compile/lift/validate/equivalence) и `frontend/features/skills/utils/behavior*.ts`, `types/behavior.ts` — живы только ради одноразового flatten | backend/frontend | Fact |
| 6.3 | `runtime/event_router.EventRouter` — только demo и тест | backend | Fact |
| 6.4 | `tools/credential_resolver.parse_binding_config` нигде не вызывается и дублирует `tools/instance_config.parse_instance_config` / `tools/web_client/config.parse_web_client_binding_config` | backend | Fact |
| 6.5 | `definition/catalog/web_client_defaults.py` + `WEB_CLIENT_DEFAULTS` дублируют `configSchema` манифеста web_client | backend | Fact |
| 6.6 | `app/api/channels/telegram_utils.default_skill_id` — deprecated обёртка над `env_default_skill_id` | backend | Fact |
| 6.7 | `SkillRunStore.find_waiting_by_conversation` (Protocol + Postgres) и `store_find_waiting` — нигде не вызываются после фазы 2 (N run на разговор) | backend | Fact |
| 6.8 | Поля `storyViewport`, `logicViewport`, `behavior`, `execution` в `SkillApi` — принимаются и отбрасываются | `definition/schemas/agent_api.py` | Fact |
| 6.9 | `ToolDefinition`/`ToolCommandDef` в `domain/tool.py` — используются только демо-сценарием `scenarios/foreman_request.py`; каталог работает на dict-манифестах | backend | Fact |
| 6.10 | `backend/.venv`, `.venv-test` — пустые venv Python 3.14 в рабочем дереве (игнорируются git) | backend | Fact |

## 7. Места, где намерение автора не восстанавливается

| # | Вопрос | Тип |
|---|---|---|
| 7.1 | Семь каталожных Tool-типов без реализации: roadmap, демонстрация библиотеки или мусор? | Unknown |
| 7.2 | Почему Behavior Graph снят (конкретные аргументы) — в документах только факт снятия | Unknown |
| 7.3 | Почему Alembic не используется при наличии конфигурации | Unknown |
| 7.4 | Должны ли `inputSchema`/`outputSchema` Action когда-либо применяться runtime | TODO |
| 7.5 | Семантика `expires_at` и таймеров в конструкторе | TODO |
| 7.6 | Целевая модель безопасности API (auth, CORS) | Unknown |
| 7.7 | Конфигурация `nginx_proxy` для доменов E.V.A. (вне репозитория) | Unknown |
| 7.8 | Планы по `amend` как изменению живого run (vs cancel+start) | TODO |
| 7.9 | Удалить ли `EVA_DEFAULT_SKILL_IDS` (deprecated, но обязательная переменная) | TODO |

## 8. Отсутствующее

- Бэкапы/восстановление для E.V.A. (нет процедур в репозитории).
- Аутентификация/авторизация API.
- Наблюдаемость worker (метрики/трейсинг) за пределами логов.
- Документация HTTP API (кроме автогенерируемой OpenAPI).
- Второй и третий «снабженческие» процессы для проверки универсальности ядра (E4).
