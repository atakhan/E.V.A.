# Goals — цели, область, ограничения, предположения

> Уровень: **Зачем**. Цели восстановлены из `architecture/*.md`, `docs_old/*_SPEC_v0.1.md` (разделы «Acceptance Criteria», «Что X НЕ делает», «Вне scope») и реального кода. Ничего из перечисленного не выдумано; где цель заявлена, но не достигнута — это помечено.

## Цели

| # | Цель | Статус в коде | Источник |
|---|------|---------------|----------|
| G1 | Описывать поведение агента декларативно: Skill = FSM (`states[]`, `initial`, `params`), Action = recipe из команд Tools | **Достигнута** — `domain/skill.py`, `domain/action.py`, FSM-холст | SKILLS_SPEC, ACTIONS_SPEC |
| G2 | Визуальный конструктор: холст редактирует ровно то, что исполняет runtime; нет промежуточной компиляции | **Достигнута** (Behavior Graph снят в 09-2026) | `docs_old/SKILLS_CONSTRUCTOR.md`, коммит `4dea5f0` |
| G3 | Runtime исполняет опубликованные неизменяемые версии; запущенный процесс не переключается на новую версию | **Достигнута** — `agent_publications`, `skill_runs.publication_version`, pin при resume | RUNTIME_SPEC §4 |
| G4 | Долгоживущие процессы: Skill Run переживает ожидание (часы/дни) и рестарт worker | **Достигнута** — статус `waiting`, durable `skill_runs`, stateless worker | RUNTIME_SPEC §8, §19 |
| G5 | Event-driven: Tools не управляют FSM, а публикуют факты; runtime решает, кому доставить | **Достигнута** — Redis Stream `eva:events`, `route_all` | EVENT_SPEC |
| G6 | Надёжная доставка: at-least-once + дедупликация + оптимистичная блокировка + DLQ | **Достигнута (MVP)** — `eva:processed_events`, `revision`, `eva:events:dlq` | RUNTIME_SPEC §16–17, §23 |
| G7 | Полная история исполнения: события, ActionRun, ToolExecution, логи API Tools | **Достигнута** — `/api/runtime/runs/{id}/history`, `tool_api_logs` | RUNTIME_SPEC §33 |
| G8 | Один разговор → N одновременных работ; акт человека классифицируется диспетчером до FSM | **Частично** — диспетчер есть (таблица правил), приёмка 2.5/6 | INTERACTION_SPEC §16 |
| G9 | Операционный контроль: cockpit (runs, cancel, timeline, simulate) | **Достигнута (v1)** — `features/runtime/` | RUNTIME_IMPLEMENTATION_STATUS |
| G10 | Деплой stage/prod в общей Docker-сети экосистемы с секретами из Infisical | **Достигнута** с оговорками (см. REVIEW: Makefile) | коммиты `defce8a`, `cc85371` |
| G11 | Пройти три существенно разных снабженческих процесса через модель без «снабженческих» сущностей в ядре | **Открыта** — реализованы `process_foreman_request`, `razgovor`, `process_supplier_request`; `negotiate_supplier`, `process_invoice` отсутствуют | agent_architecture §30 |

## Область проекта (in scope)

- Конструктор агентов: Agents, Skills (FSM), Actions (recipe), Tools (типы и инстансы), credentials, валидация, публикация.
- Runtime: приём событий, маршрутизация, интерпретация FSM, исполнение Actions/Tools, ожидание/возобновление, отмена, retry/timeout на уровне Action, история, метрики.
- Каналы: Telegram (webhook и long polling), внешний веб-клиент (ingress/outbox HTTP-контракт), прямой API для тестов.
- LLM как Tool через Polza.ai (OpenAI-совместимый API) и локальная заглушка.
- Слой взаимодействия человек ↔ агент: диспетчер актов, фокус, снимок стола, присутствие.

## Вне области (явно, по источникам)

| Не делаем | Почему / где сказано |
|---|---|
| Микросервисы, Kubernetes, Kafka, Temporal на первом этапе | `backend_architecture_v1.md` §2, §18, §26 — модульный монолит + workers, собственный FSM-runtime |
| Runtime как ERP / система учёта; хранение бизнес-данных в runtime | RUNTIME_SPEC §2; INTERACTION_SPEC R1.4 — стол живёт в веб-клиенте, платформа читает snapshot и шлёт патчи |
| Универсальный NLU «один скилл на всё» | INTERACTION_SPEC §15; `INTERACTION_FUNDAMENTAL_PROBLEM.md` §4 — выбор работы = классификация акта, не понимание текста |
| LLM выбирает Action внутри FSM | `ARCHITECTURE_DOCS_ALIGNMENT.md` decision #6 — FSM выбирает action id по event/guard; LLM — Tool в recipe |
| Planner (приоритизация и планирование очереди работ) | agent_architecture §23, §29 — отложен за пределы v0.1 |
| Multi-tenant изоляция, квоты | agent_architecture §29 — открыто |
| Distributed tracing, replay в production | RUNTIME_IMPLEMENTATION_STATUS — ❌ / admin-only |
| Параллельные группы шагов recipe | RUNTIME_SPEC §24 — ❌ deferred |
| Composition Action-in-Action | ACTIONS_SPEC §24 — используйте FSM Skill |
| Отдельные сущности Session / Context Manager / Task Manager | agent_architecture §16–§18 — покрываются Agent / Skill Run / Conversation / Tools |

## Ограничения, которые задаёт сам проект

- **Fact.** Skill ссылается только на **id Action**, никогда на команды Tools напрямую (`validate_skill`: `unknown_action`).
- **Fact.** Recipe step ссылается на **инстанс** Tool агента (или на тип, если инстанс единственный и включён); неоднозначность — ошибка публикации.
- **Fact.** Publish отклоняется при любой ошибке валидации (`AgentService.publish` → `ValueError`).
- **Fact.** Все настройки backend обязаны быть заданы явно в окружении; отсутствие любой переменной — падение при старте (`app/config.py`, коммит `e4093bc`).
- **Fact.** Runtime читает публикацию, а не черновик; изменения черновика не влияют на живых агентов до publish.

## Предположения, лежащие в основе

| Предположение | Тип | Комментарий |
|---|---|---|
| Поведение агента можно выразить конечным автоматом с детерминированными guards | Fact (дизайн) | Guards — безопасный мини-язык сравнений, не произвольный код |
| LLM — источник структурированных результатов внутри Action, а не «мозг», управляющий процессом | Fact (дизайн) | `polza_ai_llm.run_structured`, `parse_request` |
| Один агент = один документ (skills + actions + tools) в JSONB; масштабы — десятки агентов, не тысячи | Inference | Нет пагинации агентов, фронтенд грузит все агенты при старте |
| Redis Streams достаточно как транспорт событий на MVP; транспорт заменим без смены доменной модели | Fact (дизайн) | `backend_architecture_v1.md` §17 |
| Внешний веб-клиент готов реализовать контракт `/eva/health`, `/eva/messages`, `/eva/context` и присылать акты с `focus`/`intent` | Fact (контракт) + Unknown (готовность реального клиента) | Эталон — `examples/web_client_stub` |
| Один экземпляр runtime worker (`consumer = "worker-1"`) | Fact (код) | Горизонтальное масштабирование worker не предусмотрено явно |

## Неопределённости

- **Unknown.** Планы по 7 каталожным Tool-типам без реализации (`memory`, `context`, `crm`, `catalog`, `web_search`, `files`, `saby`): это roadmap или задел «на вырост» — в материалах не сказано.
- **Unknown.** Целевая модель прав/акторов (INTERACTION R9.2): в коде актёр — поле `user_id`, конфликтов двух голосов нет.
- **TODO.** Критерий G11 (три процесса снабжения) не закрыт; второй и третий процессы не начаты.
