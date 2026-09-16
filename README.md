# E.V.A.

<p align="center">
  <img src="frontend/public/eva-logo.png" alt="E.V.A. logo" width="120" />
</p>

Engine for Versatile Agents.

Стек: **FastAPI** (backend) + **Vue 3 / TypeScript** (frontend) + **Docker Compose**.

## Документация

| Слой | Путь |
|------|------|
| Нормативные спеки | [`docs/*_SPEC_v0.1.md`](docs/) |
| Конструктор Skills (обзор модели) | [`docs/SKILLS_CONSTRUCTOR.md`](docs/SKILLS_CONSTRUCTOR.md) |
| Архив устаревших docs | [`docs/archive/`](docs/archive/) |
| Взаимодействие человек ↔ агент | [`docs/INTERACTION_SPEC_v0.1.md`](docs/INTERACTION_SPEC_v0.1.md) |
| План слоя взаимодействия | [`docs/INTERACTION_IMPLEMENTATION_PLAN.md`](docs/INTERACTION_IMPLEMENTATION_PLAN.md) |
| Заметки по внедрению | [`docs/INTERACTION_IMPLEMENTATION_NOTES.md`](docs/INTERACTION_IMPLEMENTATION_NOTES.md) |
| Разбор заметок (архитектура) | [`docs/INTERACTION_NOTES_ARCHITECTURE_REVIEW.md`](docs/INTERACTION_NOTES_ARCHITECTURE_REVIEW.md) |
| Модель конторы (директор / стойка / бюро) | [`docs/INTERACTION_OFFICE_MODEL.md`](docs/INTERACTION_OFFICE_MODEL.md) |
| Конституция аналитического бюро | [`docs/INTERACTION_BUREAU_MODEL.md`](docs/INTERACTION_BUREAU_MODEL.md) |
| Зачем была аналогия конторы | [`docs/INTERACTION_FUNDAMENTAL_PROBLEM.md`](docs/INTERACTION_FUNDAMENTAL_PROBLEM.md) |
| Три проекции ситуации (оператор / домен / агентство) | [`docs/INTERACTION_WORLD_MODEL.md`](docs/INTERACTION_WORLD_MODEL.md) |
| Контора vs сборка | [`docs/INTERACTION_OFFICE_GAP.md`](docs/INTERACTION_OFFICE_GAP.md) |
| Концептуальная архитектура | [`architecture/`](architecture/) |
| Статус runtime (код vs spec) | [`docs/RUNTIME_IMPLEMENTATION_STATUS.md`](docs/RUNTIME_IMPLEMENTATION_STATUS.md) |
| Согласование architecture ↔ docs | [`docs/ARCHITECTURE_DOCS_ALIGNMENT.md`](docs/ARCHITECTURE_DOCS_ALIGNMENT.md) |

## Разработка (hot reload)

```bash
cp backend/.env.example backend/.env
cp examples/web_client_stub/.env.example examples/web_client_stub/.env
docker compose up --build
```

Первый запуск собирает образы и ставит зависимости. Дальше изменения в коде подхватываются автоматически:

- **frontend** — Vite HMR (`frontend/src`, конфиги)
- **backend** — uvicorn `--reload` (`backend/app`)

- Frontend: http://localhost:5173
- Runtime Cockpit: http://localhost:5173/runtime (глобально) · `/:slug/runtime` (per-agent)
- Backend API: http://localhost:8000/api/hello
- Health: http://localhost:8000/health

Пересборка нужна только если менялись `package.json`, `package-lock.json` или `requirements.txt`:

```bash
docker compose up --build
```

## Production

```bash
cp backend/.env.example backend/.env
docker compose -f docker-compose.prod.yml up --build
```

Frontend отдаётся через nginx (порт 5173 → 80 внутри контейнера).

## Локально без Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Vite проксирует `/api` и `/health` на backend (порт 8000).

## Структура backend

```
backend/
├── app/              # FastAPI, API routes
├── domain/           # модели Agent, Skill, Action, Event
├── definition/       # мапперы, валидация, каталог
├── runtime/          # FSM, skill runner, action executor
├── infrastructure/   # Postgres, Redis
├── tools/            # реализации Tools (пакет на инструмент)
│   ├── llm/
│   ├── telegram/
│   ├── polza/
│   └── web_client/
├── workers/
└── tests/
```

Импорт Tools — через пакеты: `from tools.telegram import TelegramTool`, `from tools.polza import PolzaClient`.

## Сценарии (шаблоны агентов)

Готовые документы агентов лежат в `backend/scenarios/` — это **шаблоны**, не автосоздание при старте:

| Файл | Агент | Назначение |
|------|-------|------------|
| `foreman_agent_document.py` | `foreman` | Telegram + LLM demo |
| `supplier_agent_document.py` | `supplier` | ai_supplier (чат + канбан) |
| `supplier_assistant_agent_document.py` | `supplier-agent` | Ассистент снабженца + skill «Разговор» |
| `conversation_skill.py` | — | Skill `razgovor` и stub-actions |

Агентов создаёте в UI E.V.A. или поднимаете в integration-тестах через `tests/scenario_fixtures.py`.

## Dev-окружение

При старте backend (по умолчанию в `docker compose`):

- **`EVA_PRUNE_EPHEMERAL_AGENTS=true`** — удаляет тестовых агентов, оставшихся после `pytest` (`eva-test-*`, `test-agent-*`, …)

Чтобы не чистить тестовых агентов — выставьте `EVA_PRUNE_EPHEMERAL_AGENTS=false` в `backend/.env`.

Полный сброс БД (удалит и логи Tools):

```bash
docker compose down -v
```

Логи Tools (`tool_api_logs`) хранятся в Postgres volume `postgres_data` и сохраняются между `docker compose up --build`. Смотреть в админке агента: раздел **Logs**.

## Тесты backend

Полный набор (нужны postgres и redis — поднимаются автоматически):

```bash
docker compose run --rm backend pytest tests/ -q
```

Только unit-тесты (без зависимостей):

```bash
docker compose run --rm --no-deps backend pytest tests/ -q -m "not integration"
```

Если `docker compose up` уже запущен:

```bash
docker compose exec backend pytest tests/ -q
```

Если pytest «завис» на integration-тесте (часто 7–8-й по счёту) — проверьте зомби-контейнеры от прерванных прогонов. Они держат соединения с Postgres:

```bash
docker ps -q --filter name=eva-backend-run | xargs -r docker stop
docker compose run --rm backend pytest tests/ -q
```
