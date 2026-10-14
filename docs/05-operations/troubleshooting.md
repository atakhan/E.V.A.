# Troubleshooting — типовые проблемы и диагностика

> Уровень: **Как использовать**. Симптом → причина (по коду) → что проверить. Команды — `docker compose`, `redis-cli`, `psql`, API проекта.

## Старт и конфигурация

| Симптом | Причина | Действие |
|---|---|---|
| Backend падает при старте: `SettingsError: missing required environment variable: X` | все переменные обязательны (`app/config.py`) | добавить `X` в `backend/.env` (dev) или в Infisical (stage/prod); список — [`setup.md`](./setup.md#конфигурация-backend-backendenv) |
| `invalid boolean for …` / `invalid value for EVA_TELEGRAM_MODE` | допустимы `1/true/yes/0/false/no`; `stub|real`; `warn|strict|off` | исправить значение |
| `docker compose up` — сервисы не стартуют, «env file … not found» | нет `backend/.env` или `examples/web_client_stub/.env` | `cp …/.env.example …/.env` |
| Frontend открылся, но «API offline», агенты только локальные | `GET /health` не ответил `{ok:true}` (backend не поднялся или прокси Vite не настроен) | `curl localhost:8100/health`; `VITE_API_PROXY`; логи `backend` |
| `make start-stage` ничего не подставляет / `${DATABASE_URL}` пуст | Infisical пути в `Makefile` (`/eva-postgres`, `/backend-environmet`) не совпадают с папками проекта; `infisical login/init` не выполнены | проверить `infisical secrets --env=staging --path=/backend-environmet`; переопределить `INFISICAL_PATH_EVA_BACKEND` |
| `make stage-secrets-upload` → `Nothing to be done` | целей нет (phony без рецепта) | заполнять секреты в UI Infisical вручную — [`deployment.md`](./deployment.md#команды-makefile) |

## События не обрабатываются

| Симптом | Причина | Действие |
|---|---|---|
| Ingress вернул `{"queued": true}`, а run не появился | worker не запущен / упал; событие пропущено | `docker compose logs -f runtime-worker`; искать `Skipping event — …` |
| Лог worker: `Skipping event — skill routing failed … No skill handles event '<type>'` | ни у одного Skill начальное состояние не ждёт этот тип; нет `defaultSkillId` | добавить переход из initial на событие или задать `defaultSkillId`; для API передать `skillId` |
| `Ambiguous routing for event … skills [...]` | несколько Skills стартуют на один тип | задать `defaultSkillId` или `skillId` в запросе |
| `Skipping event — agentSlug missing` | событие опубликовано без `agentSlug` (прямой `XADD`/замена клиента) | публиковать через `publish_event(event, agent_slug=…)` |
| `Skipping event — runtime not resolved … No publication for agent` | агент не опубликован или закреплённая версия отсутствует | Publish в UI; `GET /api/agents/{slug}/publications` |
| HTTP 422 на ingress Telegram/Web | та же маршрутизация (кроме `web.*`, которые принимаются) | см. выше |
| HTTP 409 `Agent is archived` | агент архивирован | unarchive |
| HTTP 401 на `/api/channels/web/...` | нет/неверный Bearer `inbound_api_key` | взять ключ из `oneTimeSecrets` при создании credential или сгенерировать новый credential |
| Run создался, но остался в прежнем состоянии («No-match … ignores event») | текущее состояние не имеет перехода на этот тип события или все guard ложны | проверить `event` и `guard` переходов; guard-синтаксис — A1; помнить про `payload.*`/`result.*` |
| Guard «не срабатывает» в `when` шага | в `when` корень `vars` — scope шага; нужно `payload.x` или `vars.vars.x` | [`02-domain/algorithms.md` §A1](../02-domain/algorithms.md#a1-язык-guard-условий) |
| `Concurrent update for message … leaving in PEL` в логе | конфликт `revision` (две обработки одного run) | сообщение остаётся в PEL; при повторении — `XPENDING eva:events eva-runtime`, `XCLAIM`/перезапуск worker; см. REVIEW (редоставка из PEL не реализована) |
| `Moved message … to DLQ after N attempts` | N неудач подряд (исключение в обработке) | `XRANGE eva:events:dlq - +` — поле `dlq_reason`, исходные данные; исправить причину, переопубликовать событие вручную |
| Дубли ответов пользователю | побочный эффект выполнен, падение до `mark_event_processed`, редоставка | смотреть `tool_api_logs` на дубликаты; идемпотентность Tool не гарантирована |

## Операции и инструменты

| Симптом | Причина | Действие |
|---|---|---|
| Run → `error`: `Tool '<id>' is not registered` | инстанс выключен или тип без реализации (`memory`, `context`, `crm`, `catalog`, `web_search`, `files`, `saby`) — такой инстанс молча не попадает в реестр | включить инстанс; выбрать реализованный тип |
| Лог worker: `Skipping event — runtime not resolved … '<instance>' enabled but credential … not found` | режим `real` (`EVA_TELEGRAM_MODE`/`EVA_POLZA_MODE`): Telegram или Polza без credential — сборка runtime падает целиком, событие пропускается. У `web_client` отсутствие credential на инстансе сборку больше не роняет: вызов без адреса и без credential инстанса вернёт `web_client application is not configured` | привязать credential и verify, либо переключить режим в `stub` |
| `Unknown tool reference` / `Ambiguous tool reference` | ссылка `tool` в шаге не разрешается в единственный включённый инстанс | в шаге указать `id` инстанса, а не тип |
| `Telegram sendMessage failed: …` / `chat_id is required` | нет `chat_id` в args и `conversation_id` в vars; плохой токен | передать `{{vars.conversation_id}}`; verify credential |
| `Web client network error` / `backend_base_url … not found` | недоступен бэкенд веб-клиента; Docker не видит `localhost` | `EVA_WEB_CLIENT_DOCKER_REWRITE=true` + `host.docker.internal`, либо имя сервиса `web-client-stub`; verify credential |
| `Polza instance … credential api_key not found` | `EVA_POLZA_MODE=real` без credential | создать credential `polza_ai_llm` или переключить в `stub` |
| Валидация: `invalid_step_input` | вход шага не проходит схему команды (тип/обязательность) | открыть шаг в редакторе Actions — форма по схеме подскажет поля |
| Валидация: `missing_credential` только на сервере, UI «зелёный» | правило есть только в backend | смотреть отчёт после `POST /validate` (Overview) |
| Логи Tools не пишутся | `ToolLogContext` создаётся только при `session` и `agent_id` (production-путь); ошибки записи глотаются | смотреть `logger.exception("Failed to append tool log…")` в логах |
| Операция «висит» в `waiting`, run `waiting` без видимой причины | `policy: needs_human` / `on_failure: needs_human` после ошибки | `GET /runs/{id}/history` → action run `waiting`, `error`; отправить событие, которое ждёт состояние |

## Таймеры и истечение

| Симптом | Причина |
|---|---|
| Таймер «не срабатывает» | нет способа создать таймер из конструктора; `process_due` вызывается только после обработки другого события того же агента ([`02-domain/mechanics.md` §M11](../02-domain/mechanics.md#m11-таймеры-partial)) |
| `expires_at` задан, но run живёт | поле не проверяется |

## Cockpit и API

| Симптом | Причина | Действие |
|---|---|---|
| `GET /api/runtime/metrics` всегда нули | счётчики in-memory процесса API; события обрабатывает процесс worker | смотреть `/runtime/summary` (из БД) |
| `GET /api/runtime/runs/{id}` → `toolCalls: []` | деталь строится из строки `skill_runs`, вызовы — в `/history` | использовать `/history` |
| Simulate: «нет публикаций» | агент не опубликован | Publish |
| Два окна UI перезаписывают правки друг друга | debounce-синхронизация всего документа без блокировок | работать в одном окне |

## Тесты

| Симптом | Действие |
|---|---|
| pytest «завис» на integration | зомби-контейнеры: `docker ps -q --filter name=eva-backend-run \| xargs -r docker stop` |
| integration-тесты `skipped` | Postgres/Redis недоступны по `DATABASE_URL`/`REDIS_URL` или `EVA_SKIP_INTEGRATION=1` |
| vitest: 2 падения в `actionSidebarMeta.test.ts` | известное состояние репозитория (каталог Tools в тесте пуст) — [`testing.md`](./testing.md#frontend-vitest) |

## Полезные запросы

```bash
# очередь и DLQ
docker compose exec redis redis-cli XINFO GROUPS eva:events
docker compose exec redis redis-cli XPENDING eva:events eva-runtime - + 10
docker compose exec redis redis-cli XRANGE eva:events:dlq - + COUNT 5
docker compose exec redis redis-cli KEYS 'eva:corr_lock:*'

# runs
docker compose exec postgres psql -U eva -d eva -c \
 "select id, agent_slug, skill_id, status, current_state, publication_version, revision, updated_at from skill_runs order by updated_at desc limit 20"
docker compose exec postgres psql -U eva -d eva -c \
 "select action_id, status, current_step, error from action_runs where skill_run_id='<run_id>' order by created_at"
```
