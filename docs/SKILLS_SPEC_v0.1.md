# Skill Specification
## AI Agent Constructor — Draft v0.1

> Статус: архитектурный draft. Назначение: определить контракт Skill как переиспользуемого поведенческого процесса агента.

## 1. Что такое Skill

**Skill = управляемый процесс решения определённого класса задач.**

Skill отвечает на вопрос: **как агент решает определённый класс задач?**

```text
Skill
└── FSM
    ├── States
    └── Event handlers
         ├── Guards
         └── Actions
```

Skill не вызывает Tools напрямую:

```text
Skill → FSM → Action → Tool
```

## 2. Граница сущностей

```text
Agent = конкретный агент и его возможности
Skill = поведение для класса задач
Action = конкретная операция
Tool = техническая capability
```

Пример:

```text
Agent: Procurement Agent
Skill: process_foreman_request
Actions: parse_request, clarify_with_foreman
Tools: telegram, llm, memory, crm
```

## 3. Skill Definition

Skill Definition — статическое, версионируемое описание процесса.

```yaml
id: procurement.process_foreman_request
version: "1.0.0"
description: "Process a foreman's purchase request"
initial: new

params:
  - name: request_id
    type: string
    required: true

states:
  new:
    on:
      request.started:
        actions:
          - ingest_channel_message
        to: analyzing

  analyzing:
    on:
      action.parse_request.completed:
        - guard: "result.missing_fields.length == 0"
          to: ready_for_review

        - guard: "result.missing_fields.length > 0"
          actions:
            - clarify_with_foreman
          to: waiting_for_foreman

  waiting_for_foreman:
    on:
      channel.message.received:
        - actions:
            - parse_foreman_response
          to: analyzing

  ready_for_review:
    on:
      human.request.approved:
        to: completed

      human.request.rejected:
        to: analyzing

  completed:
    final: true
```

## 4. FSM

В v0.1 каждый Skill содержит одну FSM.

FSM описывает:

- initial state;
- states;
- events;
- guards;
- actions;
- target states;
- final states.

FSM не знает реализации Telegram, CRM, LLM, Memory и других Tools.

## 5. State

State описывает текущее положение конкретного Skill Run.

Примеры:

```text
new
analyzing
waiting_for_foreman
ready_for_review
completed
```

State не должен содержать прямой код интеграций.

## 6. Initial и Final State

Каждый Skill имеет один `initial` state.

State может быть:

```yaml
final: true
```

Попадание в final state означает завершение Skill Run.

## 7. Events

Skill реагирует на события:

```text
channel.message.received
request.started
human.request.approved
human.request.rejected
supplier.reply.received
invoice.received
```

Skill не ищет Events самостоятельно. Runtime доставляет подходящие Events активным Skill Runs.

## 8. Event Handler

Event handler имеет структуру:

```text
Event
→ optional Guard
→ Actions
→ Next State
```

Отдельную сущность `Transition` в v0.1 не вводим.

## 9. Guards

Guard — детерминированное условие выбора ветки FSM.

```yaml
- guard: "result.confidence >= 0.90"
  to: ready_for_review
```

Guards должны быть ограничены безопасным expression engine и не содержать произвольного исполняемого кода.

## 10. Actions

FSM вызывает Actions по ID:

```yaml
actions:
  - parse_request
```

Skill не знает внутренний Recipe Action.

```text
Skill → Action → Tool Commands
```

## 11. on_enter

State может иметь Actions, выполняемые при входе:

```yaml
waiting_for_foreman:
  on_enter:
    - clarify_with_foreman
```

## 12. Skill Run

**Skill Definition** — описание процесса.

**Skill Run** — конкретный экземпляр выполнения.

```text
Skill Definition:
    procurement.process_foreman_request@1.0.0

Skill Run #8291:
    skill = procurement.process_foreman_request@1.0.0
    state = waiting_for_foreman
    params:
      request_id: 123
```

Один Skill может иметь много одновременно работающих Runs.

## 13. Skill Run lifecycle

Минимально:

```text
CREATED → RUNNING → WAITING → RUNNING → COMPLETED
```

Дополнительно:

```text
FAILED
CANCELLED
```

Lifecycle управляется Runtime.

## 14. Waiting и long-lived processes

Skill может приостановиться, ожидая внешнее событие:

```text
clarify_with_foreman
↓
WAITING_FOR_FOREMAN
↓
suspend
```

Позже:

```text
channel.message.received
↓
resume Skill Run
```

Долгоживущий процесс принадлежит Skill Run, а не Action.

## 15. Local variables

Skill Run может хранить локальные переменные:

```text
variables:
  clarification_attempts: 2
  last_confidence: 0.73
  selected_supplier_id: 42
```

Это не Memory.

```text
Skill Run variables = текущее состояние выполнения
Memory = долговременное знание
```

## 16. Action Result

Результат Action может участвовать в Guards и выборе следующего State.

```yaml
action.parse_request.completed:
  - guard: "result.complete == true"
    to: ready
  - guard: "result.complete == false"
    actions:
      - clarify_with_foreman
    to: waiting_for_foreman
```

## 17. Event vs Action Result

**Domain Event** — внешний факт:

```text
supplier.reply.received
channel.message.received
human.request.approved
```

**Action completion event** — синтезируется Runtime после завершения Action:

```text
action.parse_request.completed
```

Паттерн: `action.<action_id>.completed`. Payload содержит Action Result; в guards доступен как `result.*`.

Оба типа могут вызывать FSM transitions, но это разные источники: внешний мир vs завершение recipe.

## 18. Multiple handlers

Один Event может иметь несколько веток с Guards:

```yaml
supplier.reply.received:
  - guard: "result.type == 'quote'"
    actions:
      - parse_supplier_quote
    to: analyzing_offer

  - guard: "result.type == 'question'"
    actions:
      - answer_supplier_question
    to: waiting_for_supplier
```

Поведение при неоднозначных Guards должно быть детерминированным и валидироваться до публикации Skill.

## 19. Inputs / Outputs

Skill может иметь входы:

```yaml
params:
  - name: request_id
    type: string
    required: true
```

И итоговый output, формируемый последними Actions или переменными Skill Run.

## 20. Skill triggering

Skill может быть запущен:

```text
Event
Command
Human request
Schedule
System condition
```

Выбор Skill для нового события — задача Runtime / routing layer, не FSM.

## 21. Concurrency

Несколько Runs одного Skill могут работать одновременно:

```text
process_request #101
process_request #102
negotiate_supplier #31
track_shipment #7
```

Каждый Run имеет собственные State, params и variables.

## 22. Correlation

Skill Run должен быть связан с необходимыми идентификаторами:

```text
request_id
conversation_id
user_id
entity_id
parent_run_id
```

Это помогает Runtime доставлять Events правильному Run.

## 23. Cancellation и Failure

Skill Run может быть отменён:

```text
RUNNING → CANCELLED
```

Ошибки Actions не обязаны завершать Skill. Возможны стратегии:

```text
retry
alternative action
human escalation
fail
```

Подробная retry/compensation policy относится к Runtime/Action.

## 24. Human-in-the-loop

Человек является одним из источников Events.

Например:

```text
READY_FOR_REVIEW
↓
human.request.approved
↓
completed
```

## 25. Skill composition

В v0.1 базовая композиция:

```text
Agent → Skills → Actions → Tools
```

Skill не должен включать другой Skill как обычный Action.

Если требуется запуск нескольких самостоятельных процессов, Runtime может создавать несколько Skill Runs.

## 26. Versioning

Skill использует SemVer и публикуется как immutable version:

```text
process_foreman_request@1.2.0
```

Каждый Skill Run фиксирует конкретную версию Skill Definition.

Изменение опубликованного Skill не меняет уже выполняющиеся Runs.

## 27. Validation

Builder должен проверять Skill до публикации:

```text
✓ initial state существует
✓ все Actions существуют
✓ все target states существуют
✓ Events валидны
✓ Guards синтаксически валидны
✓ final states корректны
✓ нет некорректных ссылок
```

Желательные проверки:

```text
✓ unreachable states
✓ dead-end non-final states
✓ ambiguous guards
✓ unused Actions
✓ impossible transitions
```

## 28. Safety

Skill Definition не должен выполнять произвольный код.

Skill не должен напрямую:

```text
читать filesystem
делать HTTP requests
исполнять shell
работать с secrets
```

Все внешние действия проходят через Actions → Tools.

## 29. Что Skill НЕ делает

Skill не должен:

- напрямую вызывать Tools;
- напрямую управлять внешними API;
- знать реализацию Tools;
- хранить долговременную Memory;
- управлять глобальными retry policies;
- писать технические логи;
- самостоятельно маршрутизировать Events;
- содержать произвольный исполняемый код.

## 30. Что Skill делает

Skill должен:

- иметь стабильный ID;
- иметь версию;
- иметь initial state;
- определять States;
- определять Event handlers;
- использовать Actions;
- поддерживать Guards;
- иметь final states;
- принимать параметры;
- быть переиспользуемым;
- поддерживать множество Skill Runs.

## 31. Acceptance Criteria v0.1

Через модель Skill должны выражаться как минимум:

```text
process_foreman_request
negotiate_supplier
process_invoice
track_shipment
daily_reflection
```

при этом Skill Definition не содержит прямых вызовов:

```text
Telegram API
CRM API
LLM API
Postgres
Redis
HTTP
```

Skill работает через:

```text
Events
States
Guards
Actions
```

## 32. Открытые вопросы

Для следующих версий остаются:

1. Полный DAG внутри Skill.
2. Composite Skills.
3. Submachine states.
4. Dynamic Skill creation.
5. Event priority и разрешение конфликтующих handlers.
6. Event propagation.
7. Parent/child Skill Runs.
8. Compensation workflows.
9. Parallel branches и join semantics.
10. Timers как first-class events.
11. Typed expressions для Guards.
12. Planner integration.
13. Формальная модель context isolation.
14. Human Gate как first-class primitive.

## 33. Итоговая модель

```text
                         AGENT
                           │
                         SKILLS
                           │
                           ▼
                          FSM
                    ┌──────┴──────┐
                    │             │
                  STATES        EVENTS
                    │             │
                    └──────┬──────┘
                           │
                    Guards + Actions
                           │
                           ▼
                        ACTIONS
                           │
                           ▼
                         TOOLS
```

Главная формула:

```text
Skill = FSM(State + Event + Guard + Action → State)
```

Runtime loop:

```text
Event
  ↓
Current State
  ↓
Guard
  ↓
Action
  ↓
Action Result
  ↓
Next State
  ↓
Wait / Continue
  ↓
Event
```

**Skill — уровень, на котором возникает поведение агента. FSM управляет поведением, Action представляет операцию, Tool обеспечивает её выполнение.**
