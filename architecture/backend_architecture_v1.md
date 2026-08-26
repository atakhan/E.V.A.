Да. И здесь я бы **не начинал с микросервисов**. У нас появилась достаточно чёткая модель домена, и сейчас важнее построить backend так, чтобы она естественно отражалась в коде.

Я бы предложил архитектуру, которую условно назвал бы:

> **Agent Runtime Platform: Definition → Execution → World**

То есть backend состоит не столько из «модулей по бизнес-функциям», сколько из трёх больших слоёв.

---

# 1. Главная архитектура

```text
                         ┌─────────────────────┐
                         │   AGENT BUILDER UI  │
                         │                     │
                         │ Canvas / Registry   │
                         └──────────┬──────────┘
                                    │
                              Definition API
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────┐
│                     AGENT PLATFORM BACKEND                   │
│                                                               │
│  ┌──────────────────┐       ┌──────────────────────────────┐  │
│  │ DEFINITION LAYER │       │       RUNTIME ENGINE         │  │
│  │                  │       │                              │  │
│  │ Agents           │       │ Event Router                 │  │
│  │ Skills           │       │ Skill Runtime                │  │
│  │ FSM              │──────►│ FSM Interpreter              │  │
│  │ Actions          │       │ Action Executor               │  │
│  │ Tools            │       │ Tool Runtime                  │  │
│  │ Versions         │       │ Scheduler / Wait             │  │
│  └──────────────────┘       └───────────────┬──────────────┘  │
│                                             │                 │
│                              ┌──────────────▼──────────────┐  │
│                              │       EVENT / JOB BUS       │  │
│                              └──────────────┬──────────────┘  │
└─────────────────────────────────────────────┼─────────────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                           Telegram          CRM             LLM
                           Saby               Web             Memory
                           Files              1C              ...
```

Но внутри я бы сделал **модульный монолит + workers**, а не 15 отдельных сервисов.

---

# 2. Почему именно модульный монолит

У нас сейчас очень быстро может возникнуть соблазн сделать:

```text
agent-service
skill-service
fsm-service
action-service
tool-service
event-service
runtime-service
memory-service
...
```

Я бы этого **не делал**.

Потому что эти сущности настолько тесно связаны:

```text
Skill
 → FSM
 → Action
 → Tool
```

что разносить их по сети на раннем этапе будет искусственным.

Лучше:

```text
backend/
    agents/
    skills/
    actions/
    tools/
    runtime/
    events/
    executions/
    memory/
    integrations/
```

но это **один backend**.

А тяжёлые/асинхронные операции выполняются worker'ами.

---

# 3. Я бы выбрал Python

Для этой задачи Python мне кажется очень естественным.

Например:

```text
Python
FastAPI
PostgreSQL
Redis
```

а дальше:

```text
Workers
Event Bus
LLM adapters
Tool adapters
```

Почему Python:

* LLM ecosystem;
* async;
* Pydantic;
* удобное описание DSL;
* хороший ecosystem для AI;
* удобно делать runtime interpreter;
* удобно работать с JSON Schema;
* удобно писать Tool SDK.

Но самое важное — **не FastAPI**.

Главное здесь — правильно спроектировать runtime.

---

# 4. PostgreSQL становится центральным storage

Я бы сделал Postgres главным хранилищем практически всего control plane.

Например:

```text
agents
agent_versions

skills
skill_versions

actions
action_versions

tools
tool_versions

skill_runs

action_runs

events

event_subscriptions

tool_executions

credentials / connections

```

И отдельно:

```text
memories
entities
entity_relations
```

если Memory будет частью платформы.

---

# 5. Очень важная идея: Definition ≠ Runtime

Это, пожалуй, одна из самых важных архитектурных границ.

У нас есть:

```text
Skill Definition
```

Например:

```yaml
skill:
  id: procurement.process_request
  version: 3

  states:
    new:
      on:
        request.received:
          actions:
            - parse_request
          to: analyzing
```

Это **описание**.

А есть:

```text
Skill Run
```

```text
id: run_93812
skill: procurement.process_request@3
state: analyzing

params:
  request_id: 18273
```

Это **живой процесс**.

И они должны быть совершенно разными сущностями.

---

# 6. Definition Layer

Я бы сделал примерно такие модули:

```text
definition/
    agents/
    skills/
    actions/
    tools/
    versions/
    validation/
```

### Agent Registry

Хранит:

```text
Agent
AgentVersion
```

Например:

```text
Procurement Agent v12
```

---

### Skill Registry

Хранит:

```text
Skill
SkillVersion
```

Skill Version содержит FSM definition.

Например:

```text
skill.process_request
version: 1.4.2
definition: JSONB
```

---

### Action Registry

```text
Action
ActionVersion
```

Например:

```text
parse_request@2
```

с recipe:

```yaml
steps:
  - context.build
  - memory.search
  - catalog.search
  - llm.run_structured
  - crm.update
```

---

### Tool Registry

И вот здесь становится интересно.

Tool — это не просто запись в БД.

Это **plugin с контрактом**.

Например:

```text
Telegram Tool
    commands:
        send_message
        get_thread

    events:
        message.received

    state:
        connected
        disconnected
```

---

# 7. Tool SDK

Я бы даже выделил отдельный концепт:

```text
Tool SDK
```

Чтобы внешний разработчик мог написать:

```python
class TelegramTool(Tool):
    ...
```

и зарегистрировать его в платформе.

Условный интерфейс:

```python
class Tool:

    manifest()

    commands()

    events()

    execute(command, input)

    health()
```

Manifest примерно:

```yaml
id: telegram
version: 1.0

commands:
  - id: send_message
    input_schema: ...
    output_schema: ...

events:
  - id: message.received
    schema: ...
```

А вот `states` я бы сделал optional.

---

# 8. Tool Adapter

Здесь есть ещё одна важная граница.

Например:

```text
Telegram Tool
```

не должен содержать внутри всю бизнес-логику Telegram.

Он просто адаптирует внешний мир к универсальному интерфейсу платформы.

```text
Telegram API
      ↓
Telegram Adapter
      ↓
Tool Interface
      ↓
Platform Event
```

То же самое:

```text
Saby
CRM
1C
Email
Web
```

---

# 9. Runtime Engine

Вот это будет **сердце всей системы**.

Я бы выделил:

```text
runtime/
    event_router/
    skill_runtime/
    fsm/
    action/
    tool/
    scheduler/
```

И runtime должен делать примерно следующее:

```text
Event
  ↓
Event Router
  ↓
Find Skill Runs
  ↓
FSM Interpreter
  ↓
Evaluate transition
  ↓
Actions
  ↓
Action Executor
  ↓
Tools
```

---

# 10. FSM Interpreter

Это реально интересный компонент.

Он получает:

```text
Skill Definition
Skill Run
Event
```

и возвращает:

```text
Transition Result
```

Например:

```python
result = fsm.handle(
    definition=skill_definition,
    state=skill_run.state,
    event=event,
)
```

Результат:

```python
TransitionResult(
    next_state="clarifying",
    actions=[
        "clarify_with_foreman"
    ]
)
```

И всё.

FSM Interpreter **не отправляет Telegram**, не вызывает LLM и не пишет CRM.

Он только отвечает:

> «Что согласно FSM должно произойти?»

Это очень чистая граница.

---

# 11. Action Executor

Получает:

```text
Action Definition
```

и выполняет его recipe.

Например:

```text
Action
parse_request

    ↓

context.build
    ↓
memory.search
    ↓
catalog.search
    ↓
llm.run_structured
    ↓
crm.update
```

Action Executor превращает это в:

```text
Tool calls
```

---

# 12. И здесь я бы сделал важное решение

**Action Recipe не должен быть Python-кодом.**

Не:

```python
def parse_request():
    ...
```

а декларативным описанием:

```yaml
id: parse_request

steps:

  - id: context
    tool: context
    command: build

  - id: memory
    tool: memory
    command: search

  - id: catalog
    tool: catalog
    command: search

  - id: llm
    tool: llm
    command: run_structured
```

Почему?

Потому что тогда:

> **Canvas → Definition → Runtime**

становится естественной цепочкой.

---

# 13. Canvas на самом деле становится IDE

И вот тут архитектура начинает становиться очень интересной.

Пользователь на Canvas рисует:

```text
          Event
            ↓
        [State]
            ↓
        Action A
            ↓
        [State]
            ↓
        Event
       /     \
      /       \
 Action B   Action C
```

Canvas сохраняет не графику.

Он сохраняет:

```text
Skill Definition
```

То есть UI — это **визуальный редактор DSL**.

Это очень важный принцип.

---

# 14. Поэтому нужен Definition Compiler / Validator

После изменения Skill:

```text
Canvas
   ↓
JSON
   ↓
Validator
   ↓
Compiler / Normalizer
   ↓
Skill Version
```

Validator проверяет:

```text
существует ли Action?
существует ли Tool?
существует ли Event?
совместимы ли schemas?
существует ли target state?
нет ли dead-end?
есть ли initial state?
валидны ли guards?
```

И только после этого:

```text
PUBLISH
```

Skill становится доступным runtime.

---

# 15. Версионирование здесь критично

Представь:

```text
Skill v1
```

уже выполняет:

```text
Skill Run #100
```

Ты меняешь FSM:

```text
Skill v2
```

Нельзя, чтобы старый Run внезапно начал исполняться по новой FSM.

Поэтому:

```text
Skill Run #100
→ skill.process_request@1.3.0
```

а новые:

```text
Skill Run #101
→ skill.process_request@1.4.0
```

Это очень важная часть backend.

---

# 16. Execution Store

Я бы отдельно сделал execution persistence:

```text
skill_runs
action_runs
tool_executions
```

Например:

```text
skill_runs

id
skill_version_id
state
status
params
context
created_at
updated_at
```

`action_runs`:

```text
id
skill_run_id
action_version_id
status
input
output
error
started_at
finished_at
```

`tool_executions`:

```text
id
action_run_id
tool_id
command
input
output
status
```

Это даст тебе невероятно полезную возможность:

> увидеть буквально всю историю «мышления» агента на уровне execution graph.

---

# 17. Event Store / Event Bus

Я бы разделил:

### Event persistence

Postgres:

```text
events
```

для истории и аудита.

### Event transport

Для доставки событий:

```text
Redis Streams
```

или:

```text
NATS JetStream
```

На MVP я бы выбрал **Redis Streams**.

Не потому что он идеален, а потому что:

* простой;
* уже часто есть в инфраструктуре;
* достаточно хорош для первой версии;
* можно позже заменить transport, не меняя domain model.

---

# 18. А вот Temporal я бы пока не ставил в центр

Есть очень сильное искушение взять:

> Temporal.

И он действительно отлично решает:

* durable execution;
* retries;
* timers;
* long-running workflows;
* recovery;
* waiting;
* distributed execution.

Но у нас есть особенность:

**FSM пользователя динамически создаётся через Canvas.**

Мы фактически строим собственный workflow DSL.

Поэтому я бы сначала сделал:

```text
собственный FSM Runtime
+
Postgres
+
Redis Streams
```

А уже потом проверил, действительно ли Temporal даёт существенную выгоду.

Возможно, в будущем Runtime станет:

```text
FSM Definition
      ↓
Workflow Compiler
      ↓
Temporal Workflow
```

Но это второй этап.

---

# 19. Как тогда работает ожидание?

Например:

```text
clarify_with_foreman
```

Action:

```text
telegram.send_message
```

завершился.

FSM:

```text
WAITING_FOR_FOREMAN
```

Skill Run сохраняется:

```text
status = waiting
state = WAITING_FOR_FOREMAN
```

Runtime больше ничего не делает.

Через 5 часов:

```text
Telegram
 ↓
message.received
 ↓
Event Bus
 ↓
Event Router
 ↓
Skill Run #9381
 ↓
FSM
```

И процесс продолжается.

Это очень мощная модель.

---

# 20. Scheduler

Для событий типа:

```text
каждый день в 20:00
```

или:

```text
через 3 дня проверить поставщика
```

нужен scheduler.

Но опять же — не обязательно отдельный сервис.

На первом этапе:

```text
Scheduler Worker
```

может читать:

```text
scheduled_events
```

из Postgres.

Например:

```text
2026-08-27 09:00
→ supplier.followup.required
```

И публиковать Event.

---

# 21. Memory я бы сделал отдельным backend-модулем

Хотя концептуально Memory — Tool.

То есть:

```text
Runtime
    ↓
Memory Tool
    ↓
Memory Service
```

Внутри:

```text
memory/
    facts
    observations
    preferences
    relations
    embeddings
```

И потенциально:

```text
Postgres + pgvector
```

вместо отдельной vector DB на первом этапе.

---

# 22. LLM тоже Tool

Это принципиально.

Runtime не должен знать:

```text
OpenAI
Anthropic
Ollama
Mistral
...
```

Он знает:

```text
llm.run
llm.run_structured
```

А Tool implementation:

```text
LLM Tool
    ↓
Provider Adapter
    ├── OpenAI
    ├── Anthropic
    ├── Ollama
    └── ...
```

Таким образом пользователь конструктора может выбрать:

```text
LLM Tool
Model: ...
```

а не переписывать Action.

---

# 23. Context тоже можно сделать Tool

Например:

```text
Context Tool

commands:
    build
    append
    summarize
```

Но внутри:

```text
Context Engine
```

может обращаться к:

```text
Memory
CRM
Entity Graph
Conversation
Skill Run
Business Data
```

Получается:

```text
                 context.build
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Memory         CRM       Conversation
          │            │            │
          └────────────┼────────────┘
                       ▼
                    Context
```

И это хорошо соответствует первоначальной идее твоего ИИ снабженца.

---

# 24. Backend в итоге может выглядеть так

Я бы сделал **один repository**:

```text
agent-platform/
│
├── apps/
│   ├── api/
│   ├── runtime-worker/
│   ├── scheduler/
│   └── event-worker/
│
├── domain/
│   ├── agents/
│   ├── skills/
│   ├── actions/
│   ├── tools/
│   └── events/
│
├── runtime/
│   ├── fsm/
│   ├── skill_runner/
│   ├── action_executor/
│   ├── tool_executor/
│   └── event_router/
│
├── infrastructure/
│   ├── postgres/
│   ├── redis/
│   ├── llm/
│   └── integrations/
│
├── tools/
│   ├── llm/
│   ├── memory/
│   ├── telegram/
│   ├── crm/
│   ├── web/
│   └── files/
│
└── sdk/
    └── tool/
```

---

# 25. Но я бы сделал ещё один слой

**Control Plane / Data Plane.**

Это уже архитектура платформы, а не просто приложения.

### Control Plane

Там пользователь **создаёт агента**:

```text
Agent
Skill
FSM
Action
Tool
Versions
Credentials
Permissions
```

### Data Plane

Там агент **живет**:

```text
Events
Skill Runs
Actions
Tool executions
LLM calls
Messages
External integrations
```

То есть:

```text
                 CONTROL PLANE
              ┌─────────────────┐
              │ Canvas           │
              │ Registry         │
              │ Versions         │
              │ Validation       │
              └────────┬────────┘
                       │
                    publish
                       │
                       ▼
                 DATA PLANE
              ┌─────────────────┐
              │ Runtime         │
              │ Event Bus       │
              │ Workers         │
              │ Tool execution  │
              └─────────────────┘
```

**Вот это, мне кажется, уже очень правильная архитектурная граница для твоего продукта.**

---

# 26. Технологический стек, который я бы попробовал

Для первой серьёзной версии:

| Задача          | Технология                                  |
| --------------- | ------------------------------------------- |
| API             | **Python + FastAPI**                        |
| ORM             | SQLAlchemy                                  |
| DB              | **PostgreSQL**                              |
| Vector          | pgvector                                    |
| Event transport | **Redis Streams**                           |
| Workers         | Python asyncio / отдельные worker processes |
| FSM             | **собственный interpreter**                 |
| DSL             | YAML/JSON + JSON Schema                     |
| LLM             | собственный LLM Tool Adapter                |
| External Tools  | Python Tool SDK                             |
| Auth            | JWT/OIDC                                    |
| Frontend        | Vue 3                                       |
| Canvas          | Vue Flow / аналогичный graph editor         |
| Observability   | OpenTelemetry                               |
| Containers      | Docker                                      |

И самое главное:

> **не Kubernetes, не микросервисы, не Kafka, не Temporal на первом этапе.**

Они могут появиться позже, если реальные нагрузки заставят.

---

# 27. А вот что я считаю самым важным

Я бы **не начинал backend с базы данных**.

Я бы сначала написал маленький чистый runtime:

```text
Event
 ↓
FSM
 ↓
Action
 ↓
Tool
 ↓
Event
```

буквально в памяти процесса.

Например:

```python
event = Event(...)

runtime.dispatch(event)

# FSM decides
# Action executes
# Tool returns result
# Event generated
# FSM continues
```

А потом уже добавить:

```text
Postgres
Redis
workers
persistence
```

Потому что **ядро твоего продукта — не CRM API и не FastAPI. Ядро — это интерпретатор модели Agent / Skill / FSM / Action / Tool.**

Если этот интерпретатор получится красивым, вся остальная backend-инфраструктура станет намного проще.

---

## И я бы следующим шагом сделал именно это

Не рисовал бы пока огромную backend-схему.

Я бы вместе с тобой спроектировал **`Agent Runtime Core`** на уровне классов и протоколов:

```text
AgentDefinition
SkillDefinition
ActionDefinition
ToolDefinition

Event
SkillRun
ActionRun
ToolExecution

FSMEngine
EventRouter
ActionExecutor
ToolExecutor
```

и взял один реальный сценарий:

```text
Telegram сообщение прораба
→ parse_request
→ обнаружили "грибки"
→ нужна уточнялка
→ отправили вопрос
→ WAITING_FOR_FOREMAN
→ через час пришёл ответ
→ Skill продолжился
→ READY
```

Если мы сможем **элегантно прогнать этот сценарий через 8–10 классов**, не добавляя всякие `ContextManagerManager`, `TaskCoordinatorFactory` и прочие архитектурные монстры 😄 — тогда, думаю, мы нащупаем настоящее ядро всей платформы.
