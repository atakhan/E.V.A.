# E.V.A. — документация

**E.V.A. (Engine for Versatile Agents)** — конструктор и исполняющая среда ИИ-агентов: человек рисует поведение агента как конечные автоматы (Skills), собирает операции (Actions) из инструментов (Tools), публикует; runtime исполняет опубликованное поведение, реагируя на события из Telegram, веб-клиента и API. Стек: FastAPI + PostgreSQL + Redis Streams, Vue 3 + TypeScript, Docker Compose.

Этот каталог — навигация. Документация построена по уровням **Зачем → Что → Из чего → Как → Как использовать**; каждый уровень читается независимо. Источник истины для описания фактического поведения — код; расхождения со спеками собраны в [`REVIEW.md`](./REVIEW.md).

## Карта

| Слой | Документы | Вопрос, на который отвечает |
|---|---|---|
| **01 Concept** | [`vision.md`](./01-concept/vision.md) · [`goals.md`](./01-concept/goals.md) · [`research-questions.md`](./01-concept/research-questions.md) · [`direction.md`](./01-concept/direction.md) · [`spatial-model.md`](./01-concept/spatial-model.md) | Зачем проект существует, что в области, что вне, что открыто; **куда двигаться дальше**; пространственная модель конструктора — исследование, не контракт |
| **02 Domain** | [`overview.md`](./02-domain/overview.md) · [`entities.md`](./02-domain/entities.md) · [`mechanics.md`](./02-domain/mechanics.md) · [`algorithms.md`](./02-domain/algorithms.md) · [`rules.md`](./02-domain/rules.md) | Из чего состоит модель: Agent / Skill / Action / Tool / Event / Skill Run; как они себя ведут; какие правила держатся |
| **03 Architecture** | [`overview.md`](./03-architecture/overview.md) · [`components.md`](./03-architecture/components.md) · [`data-flow.md`](./03-architecture/data-flow.md) · [`integrations.md`](./03-architecture/integrations.md) · [`constructor-world-axis.md`](./03-architecture/constructor-world-axis.md) | Как модель реализована системой: процессы, слои, потоки, внешние контракты; стол конструктора (адреса → каналы → агент → навыки) |
| **04 Code** | [`structure.md`](./04-code/structure.md) · [`modules.md`](./04-code/modules.md) · [`implementation.md`](./04-code/implementation.md) | Где что лежит, ключевые классы, особенности реализации, где менять |
| **05 Operations** | [`setup.md`](./05-operations/setup.md) · [`development.md`](./05-operations/development.md) · [`testing.md`](./05-operations/testing.md) · [`deployment.md`](./05-operations/deployment.md) · [`troubleshooting.md`](./05-operations/troubleshooting.md) | Как установить, настроить, запустить, тестировать, собрать, развернуть, чинить |
| **06 Experiments** | [`README.md`](./06-experiments/README.md) | Архитектурные эксперименты: Behavior Graph (снят), слой Interaction (2.5/6), foreman happy path |
| **07 Decisions** | [`README.md`](./07-decisions/README.md) | 23 решения: контекст → альтернативы → выбор → причина → последствия |
| **Review** | [`REVIEW.md`](./REVIEW.md) | Противоречия документации и кода, дефекты, мёртвый код, неизвестные места |

## С чего начать

**Новичку (понять проект без кода):** [`01-concept/vision.md`](./01-concept/vision.md) → [`02-domain/overview.md`](./02-domain/overview.md) → [`02-domain/mechanics.md`](./02-domain/mechanics.md) (M1–M8) → [`06-experiments/README.md`](./06-experiments/README.md) E3 как сквозной пример.

**Разработчику (начать работать с кодом):** [`05-operations/setup.md`](./05-operations/setup.md) → [`05-operations/development.md`](./05-operations/development.md) → [`03-architecture/overview.md`](./03-architecture/overview.md) → [`04-code/structure.md`](./04-code/structure.md) → [`04-code/modules.md`](./04-code/modules.md) (таблица «Где менять, если нужно…»).

**Разработчику (изменить механику):** найти механику в [`02-domain/mechanics.md`](./02-domain/mechanics.md) → правила в [`02-domain/rules.md`](./02-domain/rules.md) → трассировка «домен → код» в [`04-code/modules.md`](./04-code/modules.md) → особенности в [`04-code/implementation.md`](./04-code/implementation.md) → тесты в [`05-operations/testing.md`](./05-operations/testing.md).

**Эксплуатации:** [`05-operations/deployment.md`](./05-operations/deployment.md) и [`05-operations/troubleshooting.md`](./05-operations/troubleshooting.md).

**ИИ-агенту:** читать [`02-domain/rules.md`](./02-domain/rules.md) (инварианты, которые нельзя ломать), [`04-code/modules.md`](./04-code/modules.md), [`04-code/implementation.md`](./04-code/implementation.md) и [`REVIEW.md`](./REVIEW.md) перед изменениями; шпаргалки в `.cursor/skills/eva-*` частично устарели (см. REVIEW §1).

## Соглашения

- **Fact / Inference / Unknown / TODO** — пометки достоверности в тексте. Без пометки — Fact по коду.
- Доменные документы не используют имена классов; архитектурные — используют имена модулей как ориентир; кодовые — точные пути.
- Снимок состояния: коммит `59535b7` (2026-09-18), исследование 2026-10-08.

## Связанные материалы вне `docs/`

| Путь | Что это |
|---|---|
| [`../README.md`](../README.md) | Быстрый старт (ссылки на `docs/*_SPEC` там устарели) |
| [`../architecture/`](../architecture/) | Концептуальные документы-основания: `agent_architecture_v1.md`, `backend_architecture_v1.md` |
| [`../docs_old/`](../docs_old/) | Предыдущее поколение документации: нормативные спеки v0.1 (Actions, Skills, Events, Tools SDK, Runtime, Tool Field Schema), слой Interaction (спека, план, заметки, review, модели «конторы»), FSM canvas, статус runtime, alignment, план архивации, `archive/` снятых идей. Полезно как справочник контрактов; актуальность — по [`REVIEW.md`](./REVIEW.md) |
| [`../.cursor/`](../.cursor/) | Rules и skills для ИИ-ассистента |
| [`../examples/web_client_stub/`](../examples/web_client_stub/) | Эталон контракта веб-клиента |
