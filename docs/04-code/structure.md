# Code structure — структура репозитория

> Уровень: **Код**. Что где лежит и по каким правилам. Размеры — на коммит `59535b7` (2026-09-18): backend ≈ 15.3k строк Python (включая 3.6k тестов), frontend ≈ 19.2k строк TS/Vue.

## Корень

```text
E.V.A./
├── backend/                 Python 3.12: FastAPI API + runtime + workers + tools
├── frontend/                Vue 3 + TypeScript + Vite + Tailwind v4 + daisyUI
├── architecture/            концептуальные документы (non-normative): agent_architecture_v1, backend_architecture_v1
├── docs/                    ЭТА документация
├── docs_old/                предыдущее поколение: нормативные спеки v0.1, заметки Interaction, archive/ (снятые идеи)
├── examples/web_client_stub эталонный бэкенд веб-клиента (FastAPI) для dev
├── infisical/{stage,prod}/  шаблоны переменных окружения для Infisical
├── .cursor/                 rules и skills для ИИ-ассистента (eva-backend, eva-frontend, eva-specs, conceptual-thinking)
├── docker-compose.yml       dev-стек (hot reload, порты на хост, web-client-stub)
├── docker-compose.stage.yml / docker-compose.prod.yml   stage/prod в сетях tetrakomnet(-stage), без портов
├── Dockerfile.backend / Dockerfile.dev.backend          prod (multi-stage, non-root, curl) / dev (reload)
├── Dockerfile.frontend / Dockerfile.dev.frontend        prod (build → nginx-unprivileged :8080) / dev (vite :5173)
├── Makefile                 цели start/stop/build/restart/logs/health для stage и prod через infisical run
└── README.md                быстрый старт (ссылки на docs/*_SPEC устарели — см. REVIEW)
```

Workspace-уровень (`../`): `.cursor → E.V.A./.cursor` (симлинк), соседние проекты экосистемы.

## Backend

```text
backend/
├── app/
│   ├── main.py                FastAPI app, CORS *, lifespan → init_db, роутеры, /health, /api/hello
│   ├── config.py              Settings: ВСЕ переменные обязательны (_require*), lru_cache
│   ├── deps.py                init_db (create_all + ALTER IF NOT EXISTS + seed catalog + prune), get_agent_service
│   └── api/
│       ├── agents.py          /api/agents CRUD, validate, publish, publications, archive
│       ├── agent_http.py      маппинг исключений сервиса → HTTP (409 archived, 404)
│       ├── credentials.py     /api/agents/{slug}/credentials (+verify, set-webhook)
│       ├── tools.py           /api/tools/catalog
│       ├── polza.py           /api/agents/{slug}/tools/polza_ai_llm/{models,balance,logs}
│       ├── web_client.py      /api/agents/{slug}/tools/web_client/{integration,logs,generate-inbound-key}
│       ├── tool_logs.py       /api/agents/{slug}/tool-logs, /stats
│       ├── runtime.py         /api/runtime/* (runs, events, cancel, history, replay, actions/execute, metrics, summary)
│       ├── runtime_demo.py    /api/runtime/demo (in-memory foreman)
│       └── channels/
│           ├── event_ingress.py   enqueue_channel_event → publish_event
│           ├── web.py             /api/channels/web/{slug}/events, outbox; verify inbound key
│           ├── web_act.py         normalize_focus / normalize_web_act
│           ├── telegram.py        /api/channels/telegram/{slug}, legacy /telegram
│           └── telegram_utils.py  normalize_telegram_update
├── domain/                    Pydantic-модели (без зависимостей от инфраструктуры)
│   ├── agent.py               AgentDefinition, SkillRun, SkillRunStatus
│   ├── skill.py               SkillDefinition, FsmState, FsmTransition, SkillParam
│   ├── action.py              ActionDefinition, ActionRecipeStep, ActionPolicy
│   ├── action_run.py          ActionRun, ToolExecution (+ статусы)
│   ├── events.py              Event, EventCorrelation, ToolResult, ActionResult
│   └── tool.py                ToolDefinition, ToolCommandDef (минимальные; каталог — dict-манифесты)
├── definition/
│   ├── services/              agent_service.py, credential_service.py, tool_api_log_service.py
│   ├── validation/            validate_agent.py, validate_skill.py, validate_tool_command_input.py
│   ├── mappers/               skill_mapper.py, action_mapper.py, event_mapper.py
│   ├── schemas/agent_api.py   Pydantic-схемы HTTP (AgentApi, SkillApi, ActionDefApi, ToolInstanceApi, …)
│   ├── catalog/               builtin_tools.py (агрегатор), builtin_events.py, field_schema.py, field_defs.py, manifests/stubs.py, web_client_defaults.py
│   └── behavior/              снятый Behavior Graph: compile, lift, validate, equivalence, materialize (flatten)
├── runtime/
│   ├── runtime_factory.py     build_runtime_service(session, slug, skill_id, version?) ← ВХОД для production
│   ├── runtime_service.py     RuntimeContext, RuntimeService (route_all, _resolve_targets, cancel_run)
│   ├── dispatcher.py          DispatchClass, DispatchDecision, classify_act
│   ├── skill_routing.py       find_skills_for_event, run_accepts_event, matching_waiting_run
│   ├── skill_resolver.py      resolve_skill_for_event (приоритеты), env fallback (deprecated)
│   ├── skill_runner.py        SkillRunner.handle, SkillRunTrace
│   ├── fsm_engine.py          FSMEngine, TransitionResult, AUTO_EVENT, action_completed_event_type
│   ├── guards.py              evaluate_guard, is_valid_guard_syntax, build_guard_scope
│   ├── expression_resolver.py resolve_value (шаблоны), build_action_input
│   ├── action_executor.py     ActionExecutor, ActionExecutionError
│   ├── tool_executor.py       ToolExecutor (+ лог), _is_transient
│   ├── tool_instance_resolver.py  normalize/list/enabled/resolve_recipe_tool/credential_by_instance
│   ├── definition_loader.py   load_runtime_catalog, build_tool_registry (сборка инстансов по типу + режимы)
│   ├── publication_loader.py  load_published_agent_body
│   ├── event_router.py        legacy in-memory EventRouter, RuntimeCatalog, RouterResult
│   ├── stores/skill_run_store.py  SkillRunStore (Protocol), InMemoryStore, store_* helpers
│   ├── desk.py / presence.py  снимок стола → vars; presence
│   ├── correlation_lock.py / event_lock.py  Redis lock; ключ блокировки
│   ├── dlq.py / metrics.py / scheduler.py / skill_run_query.py / tool_log_context.py / exceptions.py
│   └── __init__.py            экспорт core-классов
├── infrastructure/
│   ├── db/{base,session}.py   Base, engine/session_scope
│   ├── models/tables.py       11 ORM-таблиц
│   ├── stores/                postgres_skill_run_store.py, postgres_action_run_store.py, postgres_tool_execution_store.py, web_client_store.py (Redis)
│   ├── redis/event_bus.py     publish_event, ensure_consumer_group, processed set
│   └── crypto/secrets.py      Fernet encrypt/decrypt
├── tools/
│   ├── base.py                Tool (Protocol), BaseTool
│   ├── registry.py            ToolRegistry
│   ├── credential_resolver.py get_*_for_binding
│   ├── instance_config.py     parse_instance_config, merge_config_defaults, validate_instance_config
│   ├── scaffold.py            генератор пакета инструмента
│   ├── llm/{manifest,stub}.py
│   ├── polza/{client,llm}.py
│   ├── telegram/{manifest,tool,stub}.py
│   ├── text/{manifest,tool,regex_utils,validators}.py
│   └── web_client/{manifest,config,http,tool}.py
├── workers/
│   ├── runtime_worker.py      process_event_data, run_worker
│   └── telegram_poller.py     poll_once, run_poller
├── scenarios/                 шаблоны документов агентов (не автосоздаются)
│   ├── foreman_agent_document.py       agent foreman: llm+text+telegram, skill process_foreman_request
│   ├── foreman_request.py              in-memory demo (EventRouter + stubs), scripted_events
│   ├── supplier_agent_document.py      agent supplier: web_client, skills chat_with_supplier + process_supplier_request
│   ├── supplier_assistant_agent_document.py  agent supplier-agent: razgovor + process_supplier_request, polza_ai_llm
│   └── conversation_skill.py           skill razgovor (IDLE→THINKING→REPLIED), actions draft_reply/send_reply
├── tests/                     pytest; маркер integration; conftest (skip без БД/Redis), scenario_fixtures
├── alembic.ini, alembic/env.py   заглушка (ревизий нет)
├── requirements.txt           fastapi, uvicorn, pydantic 2, sqlalchemy 2, psycopg2, alembic, redis, cryptography, httpx, pytest
├── pytest.ini                 pythonpath=., testpaths=tests, marker integration
└── .env.example               полный список переменных (dev-значения)
```

### Правила слоёв (по `.cursor/rules/eva-backend.mdc`)

- `domain → definition → runtime → app / workers`; `infrastructure` — общий низ.
- Один пакет на Tool: `tools/<name>/` с `manifest.py`, `tool.py`, `__init__.py` (экспорт); импорт через пакет (`from tools.telegram import TelegramTool`).
- Новый Tool: пакет → манифест в `definition/catalog/builtin_tools.py` → ветка сборки в `runtime/definition_loader._build_tool_for_binding` → (фронтенд подхватит каталог автоматически).

## Frontend

```text
frontend/
├── index.html, vite.config.ts (alias @ → src, proxy /api и /health → VITE_API_PROXY, vitest), tsconfig*.json
├── nginx.prod.conf            SPA fallback, кеш статики, security headers, :8080
├── public/                    eva-logo.png и статика
└── src/
    ├── main.ts                loadToolCatalog() → createApp
    ├── App.vue                <RouterView/>
    ├── style.css              Tailwind v4 + daisyUI
    ├── router/{index,paths,guards}.ts
    ├── shared/{components,layout,schema,utils}
    └── features/
        ├── agents/{components,composables,services,types,utils,views}
        ├── constructor/{components,composables,types,views}
        ├── skills/{components,composables,fixtures,types,utils,utils/geometry,views}
        ├── actions/{components,composables,types,utils,views}
        ├── tools/{components,composables,registry,services,types,utils,views}
        ├── runtime/{components,composables,services,types,utils,views}
        └── workspace/{components,config,views}
```

Пустые каталоги-остатки: `src/components/{canvas,home}`, `src/composables`, `src/data`, `src/types`, `src/utils`, `src/views` (ничего не импортируют) — REVIEW.

### Соглашения

- Feature-based: каждая фича — `views` (страницы), `components`, `composables` (`useX`), `services` (API-клиенты и stores), `types`, `utils` (чистые функции + `*.test.ts`).
- Пути строятся только через `router/paths.ts`.
- Данные с API — camelCase; типы в `features/*/types` зеркалят `definition/schemas/agent_api.py`.
- Нормализация входящих документов — `normalizeSkill`, `normalizeAction`, `normalizeToolBinding` (включая миграцию legacy-форматов).

## Тесты

- Backend: `backend/tests/*.py` — 138 тестов (114 unit + 24 integration). Spec-тесты: `test_actions_spec.py`, `test_skills_spec.py`, `test_events_spec.py`; interaction: `test_dispatcher.py`, `test_interaction_routing.py`, `test_phase1_4.py`, `test_web_act.py`; runtime: `test_runtime_gaps.py`, `test_runtime_cockpit_api.py`, `test_skill_resolver.py`, `test_tool_instances.py`; tools: `test_text_tool.py`, `test_telegram_tool.py`, `test_polza_ai_llm.py`, `test_tool_logging.py`; каталог: `test_catalog_completeness.py`, `test_field_schema.py`.
- Frontend: `src/**/*.test.ts` (vitest, environment node): геометрия/маршрутизация, YAML, валидация Skill, импорт пакета, behavior compile, схема полей, библиотека Tools, sidebar meta, светофор канала (`evaluateWorldLink.test.ts`).

Как запускать — [`05-operations/testing.md`](../05-operations/testing.md).
