# Setup — установка и конфигурация

> Уровень: **Как использовать**. Все команды взяты из `README.md`, `docker-compose*.yml`, `Dockerfile*`, `Makefile`, `package.json`, `requirements.txt` и проверены по ним. Ничего не придумано.

## Требования

| Компонент | Версия (по конфигам) | Зачем |
|---|---|---|
| Docker + Docker Compose v2 | compose-файлы без поля `version` | основной способ запуска |
| Python | 3.12 (`Dockerfile*.backend`: `python:3.12-slim`) | backend без Docker |
| Node.js | 22 (`node:22-bookworm-slim`) | frontend без Docker |
| PostgreSQL | 15 | хранилище |
| Redis | 7 | шина событий, блокировки, кеш |
| Infisical CLI | — | только stage/prod |

Образы собираются на Python 3.12; для локального запуска используйте ту же версию (например, `uv venv --python 3.12`), чтобы совпадать с Docker. Проверено: unit-тесты проходят на 3.12 с зависимостями из `requirements.txt`.

## Установка (Docker, рекомендуемый путь)

```bash
cd E.V.A.
cp backend/.env.example backend/.env
cp examples/web_client_stub/.env.example examples/web_client_stub/.env
docker compose up --build
```

Что произойдёт:

1. Поднимутся `postgres` (хост `:5433` → контейнер `:5432`), `redis` (хост `:6380` → `:6379`) с healthcheck.
2. `backend` (хост `:8100` → контейнер `:8000`, uvicorn `--reload`), `runtime-worker`, `telegram-poller` — из `Dockerfile.dev.backend`; код монтируется (`./backend:/app`).
3. `frontend` (:5173, Vite HMR) — `Dockerfile.dev.frontend`; `node_modules` в отдельном volume.
4. `web-client-stub` (:8765) — эталонный бэкенд веб-клиента.
5. При старте backend: `create_all` + добавление колонок, посев каталога Tools, удаление эфемерных тест-агентов (если `EVA_PRUNE_EPHEMERAL_AGENTS=true`).

Пересборка образов нужна только при изменении `requirements.txt` или `package(-lock).json`.

## Установка без Docker

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Python 3.12
pip install -r requirements.txt
set -a; source .env; set +a                           # все переменные обязательны
uvicorn app.main:app --reload --port 8100
# отдельными процессами при необходимости:
python -m workers.runtime_worker
python -m workers.telegram_poller
```

В `.env` для локального запуска замените хосты `postgres`/`redis` на `localhost` и порты на опубликованные: Postgres `5433`, Redis `6380` (в `.env.example` адреса рассчитаны на Docker-сеть, где порты по-прежнему `5432` и `6379`).

Frontend:

```bash
cd frontend
npm install        # или npm ci
npm run dev        # :5173; прокси /api и /health → VITE_API_PROXY (по умолчанию http://localhost:8100)
```

## Конфигурация backend (`backend/.env`)

Все переменные **обязательны** (см. [`04-code/implementation.md` §1](../04-code/implementation.md#1-настройки-всё-или-ничего)). Значения из `.env.example`:

| Переменная | Dev-значение | Назначение |
|---|---|---|
| `PORT` | `8000` | порт uvicorn внутри контейнера; на хост в dev публикуется `8100` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `eva` / `eva` / `eva` | контейнер Postgres (dev читает тот же `.env`) |
| `DATABASE_URL` | `postgresql+psycopg2://eva:eva@postgres:5432/eva` | SQLAlchemy |
| `REDIS_URL` | `redis://redis:6379/0` | шина, locks, кеш |
| `EVA_EVENT_STREAM` | `eva:events` | имя Redis Stream (DLQ = `<stream>:dlq`) |
| `EVA_EVENT_CONSUMER_GROUP` | `eva-runtime` | consumer group worker |
| `EVA_EVENT_MAX_ATTEMPTS` | `5` | попыток обработки сообщения до DLQ |
| `EVA_AUTO_MIGRATE` | `true` | `create_all` + `ALTER … IF NOT EXISTS` при старте API |
| `EVA_CREDENTIALS_KEY` | *(пусто)* | Fernet-ключ шифрования credentials; пусто → хранение открытым текстом (dev only). Сгенерировать: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `EVA_TELEGRAM_MODE` | `stub` | `stub` — in-memory Telegram; `real` — Bot API через credentials |
| `EVA_TELEGRAM_POLLING` | `false` | включить long polling в `telegram-poller` |
| `EVA_WEBHOOK_BASE` | *(пусто)* | публичный базовый URL для `setWebhook` (например, ngrok) |
| `EVA_POLZA_MODE` | `real` | `stub` — локальная заглушка под id `polza_ai_llm`; `real` — Polza.ai |
| `POLZA_API_BASE` | `https://polza.ai/api/v1` | база API Polza |
| `POLZA_DEFAULT_MODEL` | `openai/gpt-4o-mini` | модель по умолчанию, если не задана в config инстанса |
| `EVA_DEFAULT_SKILL_IDS` | *(пусто)* | **deprecated** `slug=skill_id,…` — fallback маршрутизации; предпочтительнее `defaultSkillId` в документе агента |
| `EVA_PUBLIC_URL` | `http://localhost:8100` | публичный URL E.V.A. для подсказок интеграции Web Client |
| `EVA_WEB_CLIENT_DOCKER_REWRITE` | `true` | заменять `localhost` в `backend_base_url` credential на `EVA_WEB_CLIENT_DOCKER_HOST` |
| `EVA_WEB_CLIENT_DOCKER_HOST` | `host.docker.internal` | хост для rewrite (в compose добавлен `extra_hosts: host-gateway`) |
| `EVA_TOOL_INPUT_VALIDATION` | `warn` | `warn` / `strict` / `off` — валидация входа команд по схеме |
| `EVA_PRUNE_EPHEMERAL_AGENTS` | `true` | удалять при старте агентов `eva-test-*`, `test-agent-*`, `web-agent-*`, `cred-agent-*` |
| `VITE_API_PROXY` | `http://backend:8000` | только для dev-сервера Vite (сервис `frontend` читает тот же `.env`) |

Stage/prod-значения — `infisical/{stage,prod}/eva-backend.env.example` (`EVA_TELEGRAM_MODE=real`, `EVA_WEB_CLIENT_DOCKER_REWRITE=false`, `EVA_PRUNE_EPHEMERAL_AGENTS=false`, публичные URL доменов).

## Конфигурация web-client stub (`examples/web_client_stub/.env`)

| Переменная | Назначение |
|---|---|
| `WEB_CLIENT_OUTBOUND_KEY` | ключ, который stub ожидает в `Authorization: Bearer` от E.V.A. (`outbound_api_key` в credential) |
| `EVA_INGRESS_URL` | куда stub шлёт акты (`/demo/send-to-eva`): `http://backend:8000/api/channels/web/<slug>/events` |
| `EVA_INBOUND_KEY` | inbound-ключ агента для ingress |

## Конфигурация frontend

- `vite.config.ts`: alias `@ → src`, dev-прокси `/api`, `/health`; `usePolling` для файловых watcher-ов в Docker; HMR на `localhost:5173`.
- Prod: статика собирается `npm run build` (`vue-tsc -b && vite build`) и отдаётся nginx (`frontend/nginx.prod.conf`, порт 8080, SPA fallback). API ожидается по относительному `/api/` — маршрутизацию делает edge-прокси.

## Первичная настройка агента (после установки)

1. Открыть `http://localhost:5173` → создать агента (slug, имя).
2. **Tools:** добавить инстансы из библиотеки; для `telegram`/`polza_ai_llm`/`web_client` создать credential и привязать (иначе валидация даст `missing_credential`). В dev с `EVA_TELEGRAM_MODE=stub`/`EVA_POLZA_MODE=stub` credentials могут быть фиктивными, но инстанс всё равно требует `credentialId`.
3. **Actions:** собрать recipe из команд включённых инстансов.
4. **Skills:** нарисовать FSM; начальное состояние должно ждать стартовое событие (`channel.message.received` для чата, `ui.request.parse_requested` для кнопки «разобрать»).
5. **Overview:** валидация → **Publish**.
6. **Runtime → Simulate:** отправить тестовое событие; или подключить канал (webhook/polling Telegram, ingress веб-клиента).

Готовые шаблоны документов — `backend/scenarios/*_agent_document.py` (используются тестами; в UI можно воспроизвести вручную или через YAML-импорт Skills).
