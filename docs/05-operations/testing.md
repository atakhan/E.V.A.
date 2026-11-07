# Testing — тесты

> Уровень: **Как использовать**. Команды — из `README.md`, `pytest.ini`, `tests/conftest.py`, `package.json`, `vite.config.ts`. Результаты прогона — фактические (2026-10-08, коммит `59535b7`).

## Backend (pytest)

### Типы тестов

| Тип | Маркер | Нужны сервисы | Кол-во |
|---|---|---|---|
| Unit | без маркера | нет | 114 |
| Integration | `@pytest.mark.integration` | Postgres + Redis (по `DATABASE_URL`/`REDIS_URL`) | 24 |

`conftest.py` при сборе тестов проверяет доступность Postgres и Redis; если недоступны (или `EVA_SKIP_INTEGRATION=1`) — integration-тесты помечаются `skip`. Интеграционные тесты создают эфемерных агентов (`eva-test-<hex>`) и удаляют их; остатки убирает `EVA_PRUNE_EPHEMERAL_AGENTS` при старте backend.

Настройки читаются из окружения — для запуска нужен загруженный `backend/.env` (в контейнере он подключён как `env_file`).

### Запуск в Docker (как в README)

```bash
# полный набор (postgres и redis поднимутся по depends_on)
docker compose run --rm backend pytest tests/ -q

# только unit
docker compose run --rm --no-deps backend pytest tests/ -q -m "not integration"

# если стек уже запущен
docker compose exec backend pytest tests/ -q
```

### Запуск локально (без Docker)

```bash
cd backend
set -a; source .env; set +a                      # DATABASE_URL/REDIS_URL должны указывать на доступные хосты
EVA_SKIP_INTEGRATION=1 python -m pytest tests/ -q -m "not integration"
```

Фактический результат (Python 3.12, зависимости из `requirements.txt`):

```text
114 passed, 24 deselected in 1.27s
```

### Что покрыто

| Область | Файлы |
|---|---|
| Контракты спек (нормализация recipe, шаблоны, guard-язык, конверт событий) | `test_actions_spec.py`, `test_skills_spec.py`, `test_events_spec.py` |
| Диспетчер и маршрутизация Interaction (resume/start/cancel/amend, фокус, lock-ключи) | `test_dispatcher.py`, `test_interaction_routing.py`, `test_phase1_4.py`, `test_web_act.py`, `test_skill_resolver.py` |
| Runtime: пин версии, ActionRun/ToolExecution, cancel, history, cockpit API | `test_runtime_gaps.py`, `test_runtime_cockpit_api.py` (integration) |
| Инстансы Tools и разрешение ссылок | `test_tool_instances.py` |
| Tools | `test_text_tool.py`, `test_telegram_tool.py`, `test_polza_ai_llm.py`, `test_tool_logging.py`, `test_tool_log_stats.py` |
| Каталог и схемы полей | `test_catalog_completeness.py`, `test_field_schema.py`, `test_validate_tool_command_input.py` |
| Сценарии агентов | `test_foreman_scenario.py` (in-memory happy path), `test_supplier_agent.py`, `test_supplier_assistant_agent.py`, `test_supplier_integration.py` |
| Агенты: архивация, prune, credentials, web client | `test_agent_archive.py`, `test_agent_prune.py`, `test_credentials_api.py`, `test_web_client.py` |
| Legacy Behavior Graph compile | `test_behavior_compile.py` |
| Конфиг | `test_config.py` |

### Чего нет (Fact: файлов/тестов не найдено)

- Тестов `runtime_worker.process_event_data` целиком (DLQ, PEL, lock) — проверяются только функции ключей.
- Тестов `telegram_poller` с реальными HTTP-ответами (есть `test_telegram_poller.py` на фильтр credentials).
- Тестов паритета валидации backend ↔ frontend.
- Тестов `scheduler.process_due`, `expires_at`.
- Нагрузочных/конкурентных тестов оптимистичной блокировки.

### Известная проблема: «зависший» pytest

Из README: если прогон «завис» на integration-тесте, проверьте зомби-контейнеры прерванных прогонов — они держат соединения с Postgres:

```bash
docker ps -q --filter name=eva-backend-run | xargs -r docker stop
docker compose run --rm backend pytest tests/ -q
```

## Frontend (vitest)

```bash
cd frontend
npm test                 # vitest run; environment node; include src/**/*.test.ts
npx vitest run <путь>    # один файл
npm run build            # vue-tsc -b && vite build — type-check как часть сборки
```

Фактический результат:

```text
Test Files  1 failed | 9 passed (10)
Tests       2 failed | 48 passed (50)
```

Падают `src/features/actions/utils/actionSidebarMeta.test.ts`: «returns ok when instance enabled and command valid» и «flags ambiguous type reference» — ожидаемые `ok`/`ambiguous`, фактически `unknown`. Причина: `resolveRecipeTool` опирается на каталог Tools, который в тестах пуст (не вызван `setToolCatalogForTests`), после переноса каталога на сервер. Исправление — вопрос кода/тестов, не документации (см. REVIEW).

`npm run build` проходит (type-check чистый, бандл ≈ 390 kB JS / 146 kB CSS).

### Что покрыто

Геометрия и ортогональная маршрутизация холста, формат подписей переходов, YAML/pack импорт Skills, `validateSkill`, компиляция legacy Behavior Graph, схема полей, индекс библиотеки Tools, sidebar-мета Actions, светофор кабеля канала (`features/agents/utils/evaluateWorldLink.test.ts`). Компонентных (Vue) и e2e-тестов нет.

## Ручная проверка end-to-end

1. `docker compose up` → создать агента по шаблону `foreman` (llm + text + telegram stub, skill `process_foreman_request`), опубликовать.
2. `curl -X POST localhost:8100/api/channels/telegram/<slug> -d '{"chat_id":"1","text":"нужны грибки"}'` → в cockpit run должен пройти `NEW → ANALYZING → CLARIFYING → WAITING_FOR_FOREMAN` (LLM-stub: «гриб» → `needs_clarification=true`; `clarify` отправит stub-сообщение).
3. Второе сообщение с тем же `chat_id` → `READY` (`completed`).
4. Проверить `GET /api/runtime/runs/<id>/history`: 2 входящих события + `action.*.completed`, action runs с tool executions.
