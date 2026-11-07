# Deployment — сборка и развёртывание (stage / prod)

> Уровень: **Как использовать**. По `docker-compose.stage.yml`, `docker-compose.prod.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `Makefile`, `infisical/`, `README.md`. Фактические дефекты Makefile отмечены — не исправлялись.

## Сборка образов

| Образ | Dockerfile | Содержимое |
|---|---|---|
| `tetrakom-eva-backend:{stage,prod}` | `Dockerfile.backend` | multi-stage: builder ставит `requirements.txt`; runtime `python:3.12-slim-bookworm` + `curl` (для healthcheck), non-root `appuser` (uid 10001), `COPY backend/ ./`, `CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}` |
| `tetrakom-eva-frontend:{stage,prod}` | `Dockerfile.frontend` | `node:22` `npm ci && npm run build` → `nginxinc/nginx-unprivileged:alpine`, `dist` → `/usr/share/nginx/html`, `frontend/nginx.prod.conf`, порт 8080 |

Один backend-образ используется тремя сервисами (API, runtime-worker, telegram-poller) с разными `command`.

`.dockerignore` исключает `*.md`, `backend/tests`, `.env*` (кроме `.env.example`), `node_modules`, `dist`, `.git`.

## Топология stage / prod

Файлы идентичны с точностью до суффикса (`-stage`/`-prod`), сети и volumes (`diff` показывает только имена):

| Сервис | Образ | Порт (expose, не publish) | Зависимости |
|---|---|---|---|
| `eva-postgres-*` | `postgres:15-alpine` | 5432 | — |
| `eva-redis-*` | `redis:7-alpine --appendonly yes` | 6379 | — |
| `eva-backend-*` | backend | 8000; healthcheck `curl /health` (30s, start 60s) | postgres, redis healthy |
| `eva-runtime-worker-*` | backend, `python -m workers.runtime_worker` | — | + backend healthy |
| `eva-telegram-poller-*` | backend, `python -m workers.telegram_poller` | — | + backend healthy |
| `eva-frontend-*` | frontend | 8080 | backend healthy |

Сеть: внешняя `tetrakomnet-stage` / `tetrakomnet` (должна существовать; `make start-*` создаёт при отсутствии). Снаружи отвечает `nginx_proxy` (отдельный проект): `https://eva-stage.tetrakom-crm-miniapp.ru`, `https://eva.tetrakom-crm-miniapp.ru`. Frontend ходит в API по относительному `/api/` — маршрутизацию `/api/` → backend делает edge-прокси. После первого деплоя E.V.A. README требует перезапустить `nginx_proxy`, чтобы он увидел контейнеры.

`restart: unless-stopped` у всех сервисов.

## Секреты и окружение

Compose stage/prod не читают `.env`: все переменные (`x-backend-environment`) берутся из окружения процесса, которое подставляет **Infisical CLI**:

```bash
# один раз на сервере
infisical login --domain https://secrets.tetrakom-crm-miniapp.ru
cd E.V.A. && infisical init                         # привязка к проекту tetrakom
export INFISICAL_DOMAIN=https://secrets.tetrakom-crm-miniapp.ru   # Makefile по умолчанию: http://127.0.0.1:8079
```

Шаблоны значений — `infisical/stage/*.env.example`, `infisical/prod/*.env.example` (три файла: backend, postgres, redis). Пароль Postgres и Fernet-ключ в шаблонах — заглушки, заменить.

**Fact (расхождение, не исправлено):**

| Где | Пути Infisical |
|---|---|
| README | `/eva-postgres`, `/eva-redis`, `/eva-backend` |
| `Makefile` (HEAD) | `--path=/eva-postgres --path=/backend-environmet` (опечатка в имени папки; `/eva-redis` удалён коммитом `2b53e41`) |
| `infisical/*/` | файлы `eva-backend`, `eva-postgres`, `eva-redis` |

Чтобы `make start-*` подхватил переменные, папки в Infisical должны называться так, как в `Makefile` (или переопределить `INFISICAL_PATH_EVA_BACKEND=/eva-backend make start-stage`). `REDIS_URL` присутствует и в шаблоне backend, поэтому отсутствие `/eva-redis` само по себе не ломает запуск.

## Команды Makefile

```bash
make start-stage     # создать сеть при необходимости; infisical run --env=staging … docker compose -f docker-compose.stage.yml up -d --build
make stop-stage      # down
make build-stage     # build (зависит от stage-secrets-check — см. ниже)
make restart-stage   # stop + start
make logs-stage      # logs -f (без infisical)
make health-stage    # exec eva-backend-stage curl /health

make start-prod | stop-prod | build-prod | restart-prod | logs-prod | health-prod   # аналогично, env=prod, docker-compose.prod.yml
```

**Fact:** цели `prod-secrets-check`, `prod-secrets-upload`, `stage-secrets-check`, `stage-secrets-upload` перечислены в `.PHONY` и используются как зависимости (`start-prod`, `build-prod`, `build-stage`), но **рецептов не имеют** (удалены при merge `59535b7`). Поэтому:

- `make start-prod` работает (зависимость — пустая phony-цель), но **никакой проверки секретов не выполняет**;
- `make stage-secrets-upload` / `make prod-secrets-upload` из README печатают `Nothing to be done` — загрузка шаблонов в Infisical через make **не работает**; заполняйте секреты в UI Infisical вручную по файлам `infisical/*/`.

Переменные Makefile можно переопределять: `COMPOSE`, `INFISICAL`, `INFISICAL_DOMAIN`, `INFISICAL_ENV_PROD` (`prod`), `INFISICAL_ENV_STAGE` (`staging`), `INFISICAL_PATH_EVA_POSTGRES`, `INFISICAL_PATH_EVA_BACKEND`.

## Порядок первого деплоя (восстановлен по README + Makefile)

1. На сервере: Docker, Infisical CLI, `infisical login`, `infisical init` в каталоге E.V.A.
2. В Infisical создать окружения `staging`/`prod` и папки с переменными по шаблонам `infisical/*/` (имена папок — см. расхождение выше).
3. Убедиться, что сеть `tetrakomnet(-stage)` существует (её создаёт `nginx_proxy` или `make start-*`).
4. `make start-stage` (или `start-prod`).
5. `make health-stage` → `{"ok":true}`; `make logs-stage` — убедиться, что `runtime_worker` стартовал (`Runtime worker started on stream eva:events`).
6. Перезапустить `nginx_proxy`.
7. В UI (`https://eva-stage…`) создать агентов, credentials (реальные токены), опубликовать. Для Telegram в prod `EVA_TELEGRAM_POLLING=false` по шаблону → использовать webhook (`set-webhook` на credential, `EVA_WEBHOOK_BASE` = публичный домен).

## Обновление

```bash
git pull
make restart-stage        # stop + start с --build
```

Схема БД обновляется при старте API (`EVA_AUTO_MIGRATE=true`): новые таблицы/колонки добавятся; удаление/изменение типов — вручную. Данные в volumes `eva_postgres_data_*`, `eva_redis_data_*` сохраняются между перезапусками; `docker compose … down -v` уничтожит их.

## Бэкапы и восстановление

В репозитории E.V.A. процедур бэкапа нет (**Unknown**). В workspace есть общие материалы `../devops_stuff/HOW_TO_BACKUP.md` и репетиция восстановления для соседнего проекта — применимость к E.V.A. не проверялась.

## CI/CD

Отсутствует (**Fact**: нет `.github/`, `.gitlab-ci.yml` и т.п.). Сборка и деплой — вручную через Makefile на сервере.

## Чеклист здоровья после деплоя

- `GET /health` → `{"ok": true}` (через прокси и `make health-*`).
- `GET /api/tools/catalog` → 12 типов.
- Логи worker без `Skipping event` / `Moved message … to DLQ`.
- `redis-cli XPENDING eva:events eva-runtime` — нет застрявших сообщений; `XLEN eva:events:dlq` = 0.
- Cockpit `/runtime` показывает агентов и публикации.
