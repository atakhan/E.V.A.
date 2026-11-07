# Development — работа с проектом локально

> Уровень: **Как использовать**. Команды — из `README.md`, compose, `package.json`, `tools/scaffold.py`, кода API.

## Запуск dev-стека

```bash
cd E.V.A.
docker compose up --build          # первый раз
docker compose up                  # далее
docker compose logs -f runtime-worker
docker compose down                # остановить
docker compose down -v             # + удалить volumes (БД, логи Tools, node_modules)
```

| URL | Что |
|---|---|
| http://localhost:5173 | Frontend (Vite HMR) |
| http://localhost:5173/runtime | Глобальный Runtime Cockpit; `/:slug/runtime` — per-agent |
| http://localhost:8100/health | `{ "ok": true }` |
| http://localhost:8100/api/hello | проверка API |
| http://localhost:8100/docs | OpenAPI (FastAPI по умолчанию) |
| http://localhost:8765 | web-client stub (`/eva/health`, `/eva/messages`, `/eva/context`, `/demo/send-to-eva`) |

Hot reload: backend — uvicorn `--reload --reload-dir /app` (все три Python-процесса монтируют `./backend`); worker и poller **не** перезапускаются автоматически — после правок runtime выполните `docker compose restart runtime-worker telegram-poller`. Frontend — Vite HMR (`usePolling`).

## Типичные dev-циклы

### Изменить поведение агента (без кода)

UI → Skills/Actions/Tools → Overview → Validate → Publish → Runtime → Simulate (`POST /api/runtime/runs` с тестовым событием; follow-up через `/api/runtime/events`). Runtime исполняет **публикацию**, черновик не влияет.

### Прогнать событие через шину (как в production)

```bash
# веб-ингресс (нужен credential web_client с inbound ключом)
curl -X POST http://localhost:8100/api/channels/web/<slug>/events \
  -H "Authorization: Bearer <inbound_api_key>" -H "Content-Type: application/json" \
  -d '{"sessionId":"web:demo:1","payload":{"text":"разбери REQ-17"},"focus":{"openEntityId":"REQ-17"}}'

# telegram webhook (упрощённый payload)
curl -X POST http://localhost:8100/api/channels/telegram/<slug> \
  -H "Content-Type: application/json" -d '{"chat_id":"123","text":"нужны грибки 10x100"}'
```

Событие уйдёт в `eva:events`; обработку смотрите в `docker compose logs -f runtime-worker` и в cockpit (`/:slug/runtime`, деталь run → timeline, tool executions).

### Синхронный путь (без worker)

```bash
curl -X POST http://localhost:8100/api/runtime/runs -H "Content-Type: application/json" \
  -d '{"agentSlug":"<slug>","skillId":"<skill>","event":{"type":"channel.message.received","payload":{"conversation_id":"c1","text":"привет"}}}'
curl -X POST http://localhost:8100/api/runtime/demo     # in-memory foreman happy path, без БД
```

### Телеграм в dev

- `EVA_TELEGRAM_MODE=stub` — сообщения не уходят; видны в `toolCalls`/логах.
- Реальный бот: `EVA_TELEGRAM_MODE=real`, создать credential `telegram` с `bot_token`, **verify**; затем либо `EVA_TELEGRAM_POLLING=true` (poller сам заберёт updates), либо `EVA_WEBHOOK_BASE=https://<ngrok>` и **set-webhook** на credential.

### Веб-клиент в dev

1. На столе конструктора добавить канал Web Client. Плюс слева от канала создаёт адрес-приложение: `backend_base_url=http://localhost:8765` (при `EVA_WEB_CLIENT_DOCKER_REWRITE=true` backend обратится к `host.docker.internal:8765`; внутри compose можно указать `http://web-client-stub:8765`), `outbound_api_key=dev-outbound-key` (как в stub `.env`), inbound-ключ сгенерируется. Тот же набор можно сохранить credential'ом инстанса на странице Tools — исходящий вызов возьмёт его, только если во `vars` нет `web_client_credential_id`.
2. В `examples/web_client_stub/.env` проставить `EVA_INBOUND_KEY` = inbound-ключ и slug агента в `EVA_INGRESS_URL`.
3. `POST http://localhost:8765/demo/send-to-eva {"sessionId":"s1","text":"..."}` → stub отправит акт в ingress; ответы агента увидите в stub (`/eva/messages`) и в `GET /api/channels/web/<slug>/sessions/s1/outbox`.
4. Панель адреса (и страница Tools → Web Client) показывает ingress URL, блок `.env` и проверку связи. Общие пути `/eva/*` редактируются на панели канала.

### Логи и диагностика

- Логи вызовов Tools: UI раздел **Logs** агента (`/:slug/logs`), API `GET /api/agents/{slug}/tool-logs`, `/stats`.
- История run: `GET /api/runtime/runs/{id}/history`.
- Метрики worker: `GET /api/runtime/metrics` (счётчики процесса API, не worker — см. REVIEW).
- Redis: `docker compose exec redis redis-cli XLEN eva:events`, `XPENDING eva:events eva-runtime`, `XLEN eva:events:dlq`, `SCARD eva:processed_events`.
- Postgres: `docker compose exec postgres psql -U eva -d eva -c "select id, skill_id, status, current_state from skill_runs order by updated_at desc limit 10"`.

## Расширение системы

### Добавить Tool-тип

```bash
cd backend
python -m tools.scaffold <name> --commands "foo,bar"    # создаст tools/<name>/{__init__,manifest,tool}.py
```

(Шпаргалка `.cursor/skills/eva-specs/tools.md` указывает форму `tools.scaffold create <name>` — подкоманды `create` в CLI нет, см. REVIEW.)

Затем вручную:

1. Заполнить `inputSchema`/`outputSchema` команд в `manifest.py` (`field(...)` из `definition/catalog/field_defs.py`; типы — `string | template | text | integer | boolean | enum | json | string_array`), `configSchema`, `credentialKind`/`credentialPolicy` при необходимости.
2. Добавить манифест в `BUILTIN_TOOLS` (`definition/catalog/builtin_tools.py`) — проверяется тестом `test_catalog_completeness.py`.
3. Добавить ветку в `runtime/definition_loader._build_tool_for_binding` (и helper в `tools/credential_resolver.py`, если нужен секрет; `verify_*` в `CredentialService`; тип в `_CREDENTIAL_TYPES` валидатора).
4. Frontend подхватит каталог через `GET /api/tools/catalog` — TS-дубликатов нет.
5. Тест в `tests/test_<name>_tool.py` по образцу `test_text_tool.py`.

### Добавить встроенное событие

`definition/catalog/builtin_events.py` → `BUILTIN_EVENT_TYPES[...]` с `required_payload`; при необходимости фабрика (как `channel_message_received`). Для подсказок в UI — `frontend/src/features/skills/utils/skillEvents.ts`.

### Добавить правило валидации

Серверная часть — `definition/validation/validate_agent.py` / `validate_skill.py`; клиентская — `frontend/src/features/agents/utils/validateAgent.ts` / `features/skills/utils/validateSkill.ts`. Коды должны совпадать (`04-code/modules.md`, A7).

### Изменить маршрутизацию/диспетчер

`runtime/dispatcher.py` (классы и regex), `runtime/skill_routing.py`, `runtime/skill_resolver.py`. Тесты: `test_dispatcher.py`, `test_interaction_routing.py`, `test_skill_resolver.py`, `test_phase1_4.py`.

### Добавить колонку в `skill_runs`

Модель `domain/agent.py` → ORM `infrastructure/models/tables.py` → `PostgresSkillRunStore.save_run/_to_domain` → `app/deps._ensure_runtime_schema` (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`) — миграций Alembic нет.

## Соглашения кода

- Backend: Python 3.12, `from __future__ import annotations`, Pydantic v2, SQLAlchemy 2.0 `Mapped[...]`; слои `domain → definition → runtime → app/workers`; импорт Tools только через пакет.
- Frontend: TypeScript strict (`vue-tsc -b` в build), feature-based layout, пути через `router/paths.ts`, Tailwind v4 + daisyUI классы в шаблонах.
- Форматтеры/линтеры в репозитории **не настроены** (нет ruff/black/eslint/prettier конфигов) — стиль поддерживается вручную.
- ИИ-ассистент: правила и шпаргалки в `.cursor/rules/*.mdc`, `.cursor/skills/*` (часть ссылок там указывает на `docs/*_SPEC` → теперь `docs_old/`).

## Полезные команды

```bash
# frontend
cd frontend && npm run dev | npm run build | npm run preview | npm test

# backend в контейнере
docker compose exec backend python -c "from definition.catalog.builtin_tools import BUILTIN_TOOLS; print([t['id'] for t in BUILTIN_TOOLS])"
docker compose exec backend python -m tools.scaffold --help

# сброс
docker compose down -v && docker compose up --build
```
