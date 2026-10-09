# Integrations — внешние системы и контракты

> Уровень: **Как устроено**. Все контракты — по коду (`tools/*`, `app/api/channels/*`, `app/api/web_client.py`, `examples/web_client_stub`, compose/Makefile).

## I1. Telegram Bot API

| Аспект | Реализация |
|---|---|
| Исходящие | `telegram.send_message` → `POST https://api.telegram.org/bot{token}/sendMessage {chat_id, text}`; `chat_id` принимает `tg:chat:<id>` или сырой id; по умолчанию — `vars.conversation_id`. Успех → `data.sent{chat_id, text, telegram_message_id}` + событие `channel.message.sent`. `parse_mode` из `configSchema` объявлен, но **не передаётся** в запрос |
| Входящие (webhook) | `POST /api/channels/telegram/{slug}` — принимает нативный update (`message`/`edited_message`: `text` или `caption`) или упрощённый `{conversation_id|chat_id, text}`; `conversation_id = tg:chat:<chat.id>`; Skill — по A4 (422, если не разрешён). `POST /api/channels/telegram` — legacy, жёстко агент `foreman` |
| Входящие (polling) | worker `telegram_poller`: для каждого credential `telegram` → `getUpdates(offset, limit 50)`; offset в Redis `eva:tg:offset:{credential_id}`; 401/404 → пропуск с предупреждением; `meta.dev_stub` / тестовые токены пропускаются |
| Credential | `{bot_token}`; verify = `getMe`; `set-webhook` → `setWebhook(url = EVA_WEBHOOK_BASE + /api/channels/telegram/{slug})` |
| Режимы | `EVA_TELEGRAM_MODE=stub` — `TelegramStubTool` копит сообщения в памяти; `real` — HTTP |
| Соответствие инстансу | входящее событие несёт `metadata.tool_instance_id` (инстанс, чей credential получил update) |

## I2. Polza.ai (LLM)

| Аспект | Реализация |
|---|---|
| Протокол | OpenAI-совместимый: `POST {POLZA_API_BASE}/chat/completions`, `GET /models`, баланс. `POLZA_API_BASE` по умолчанию `https://polza.ai/api/v1` |
| Команды | `run` (messages или prompt/system → `text`), `run_structured` (`response_format` = `json_schema` при заданной schema, иначе `json_object` → `structured`, `ok`), `parse_request` (text → `parsed`, `needs_clarification`; strict json_schema) |
| Модель | `config.model` инстанса → `POLZA_DEFAULT_MODEL` (`openai/gpt-4o-mini`); `temperature`/`max_tokens` из args |
| Credential | `{api_key}` (`credentialPolicy: shared_allowed` — один ключ на несколько инстансов) |
| Логи | каждый вызов пишется в `tool_api_logs` с `model`, `usage`, превью промпта/ответа (секреты маскируются); UI — панель Polza (models, balance, logs) |
| Режимы | `EVA_POLZA_MODE=stub` — под id `polza_ai_llm` работает `LlmStubTool` (демо-эвристика «гриб»); `real` — HTTP (требует credential) |

## I3. Внешний веб-клиент (ai_supplier / stub)

Двусторонний HTTP-контракт. E.V.A. — и сервер (ingress, outbox), и клиент (outbound к бэкенду веб-приложения).

**Outbound (E.V.A. → веб-клиент)**, пути настраиваются в `config` инстанса `web_client`:

| Команда | HTTP | Тело / ответ |
|---|---|---|
| health (verify) | `GET {backend_base_url}{healthPath=/eva/health}` | 200 |
| `send_message` | `POST {sendMessagePath=/eva/messages}` | `{sessionId, text, meta{workspace_update?, ui_proposal?, presence?, …}}` |
| `get_snapshot` | `GET {getSnapshotPath=/eva/context}?sessionId=…` | JSON снимка (ожидается `workspace.requests[]` для оверлея сущности) |

Авторизация: `authStyle` = `bearer` (`Authorization: Bearer <outbound_api_key>`) или `x-api-key`. Таймаут `timeoutSec` (30). При `EVA_WEB_CLIENT_DOCKER_REWRITE=true` `localhost`/`127.0.0.1` в `backend_base_url` заменяются на `EVA_WEB_CLIENT_DOCKER_HOST` (`host.docker.internal`) — чтобы backend в Docker достучался до клиента на хосте.

**Inbound (веб-клиент → E.V.A.):**

| Маршрут | Назначение |
|---|---|
| `POST /api/channels/web/{slug}/events` | акт человека: `{sessionId, type="channel.message.received", skillId?, actorId?, focus?{view, openEntityId, selectedEntityIds}, intent?, entityIds?, payload{text|message, …}}`; `Authorization: Bearer <inbound_api_key>`; ответ `{ok, queued, messageId, eventId}`; 401/404/409/422 |
| `GET /api/channels/web/{slug}/sessions/{sessionId}/outbox` | последние исходящие сообщения агента в эту сессию (Redis, 24 ч) |
| `GET /api/agents/{slug}/tools/web_client/integration?credentialId` | подсказки интеграции: ingressUrl, outboxUrlTemplate, hint ключа, outbound URLs (включая docker-rewrite), пути |
| `POST /api/agents/{slug}/tools/web_client/generate-inbound-key` | сгенерировать inbound-ключ |

Credential `web_client`: `{backend_base_url, outbound_api_key, inbound_api_key}`; `inbound_api_key` генерируется при создании, если не задан, и возвращается один раз (`oneTimeSecrets`).

**Эталон:** `examples/web_client_stub/main.py` (FastAPI :8765): `/eva/health`, `/eva/messages` (проверяет Bearer `WEB_CLIENT_OUTBOUND_KEY`, складывает сообщения), `/eva/context` (снимок), `/demo/send-to-eva` (прокси на ingress с `EVA_INBOUND_KEY`). В dev-compose поднимается как сервис `web-client-stub`.

**Соседний проект:** `ai_supplier` в этом же workspace реализует реальный клиент (упоминается в спеках Interaction и в описании агента `supplier-agent`); его код вне E.V.A. и здесь не документируется.

## I4. PostgreSQL

- Версия образа `postgres:15-alpine`; драйвер `psycopg2`; SQLAlchemy 2.0 ORM.
- Схема создаётся `create_all` при старте API (`EVA_AUTO_MIGRATE=true`) + idempotent `ALTER TABLE`. Alembic присутствует (`alembic.ini`, `alembic/env.py` — заглушка), ревизий нет.
- Dev: на хост публикуется `5433` (в контейнере по-прежнему `5432`); stage/prod — только внутри Docker-сети.

## I5. Redis

- `redis:7` (prod/stage — `redis:7-alpine --appendonly yes`).
- Роли и ключи — таблица в [`overview.md`](./overview.md#хранилища-и-их-роли). Один consumer group `EVA_EVENT_CONSUMER_GROUP` (`eva-runtime`), один consumer `worker-1`.

## I6. Infisical (секреты stage/prod)

- Compose-файлы stage/prod не читают `.env`; переменные подставляет `infisical run --env=<staging|prod> --path=… -- docker compose …`.
- Шаблоны значений: `infisical/{stage,prod}/eva-{backend,postgres,redis}.env.example`.
- **Fact (расхождение):** `Makefile` использует пути `/eva-postgres` и `/backend-environmet` (опечатка в имени, коммит `2b53e41` «removed extra path»), README описывает `/eva-postgres`, `/eva-redis`, `/eva-backend`. Цели `*-secrets-check` / `*-secrets-upload` объявлены `.PHONY`, но рецептов не имеют (no-op). См. REVIEW и [`05-operations/deployment.md`](../05-operations/deployment.md).
- Домен Infisical: `INFISICAL_DOMAIN` (по умолчанию `http://127.0.0.1:8079`, на сервере — `https://secrets.tetrakom-crm-miniapp.ru`).

## I7. nginx_proxy (edge)

- Отдельный проект workspace (`../nginx_proxy`). Stage/prod-стеки E.V.A. не публикуют порты; подключаются к внешним сетям `tetrakomnet-stage` / `tetrakomnet`.
- Ожидаемая маршрутизация (по README): `https://eva(-stage).tetrakom-crm-miniapp.ru/` → `eva-frontend-*` (:8080, nginx-unprivileged со SPA-fallback), `/api/` и `/health` → `eva-backend-*` (:8000). Конфигурация самого прокси — вне репозитория E.V.A. (**Unknown** здесь).

## I8. Соседние проекты workspace (контекст)

`ai_supplier`, `sous`, `foreman_miniapp`, `tetrakom_supplier_service` и др. — отдельные репозитории той же экосистемы. E.V.A. зависит от них только через HTTP-контракт веб-клиента (I3) и общую Docker-сеть/прокси (I7).
