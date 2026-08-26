# E.V.A.

Engine for Versatile Agents.

Стек: **FastAPI** (backend) + **Vue 3 / TypeScript** (frontend) + **Docker Compose**.

## Разработка (hot reload)

```bash
docker compose up --build
```

Первый запуск собирает образы и ставит зависимости. Дальше изменения в коде подхватываются автоматически:

- **frontend** — Vite HMR (`frontend/src`, конфиги)
- **backend** — uvicorn `--reload` (`backend/app`)

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api/hello
- Health: http://localhost:8000/health

Пересборка нужна только если менялись `package.json`, `package-lock.json` или `requirements.txt`:

```bash
docker compose up --build
```

## Production

```bash
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
