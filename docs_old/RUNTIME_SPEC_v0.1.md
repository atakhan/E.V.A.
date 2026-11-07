# Runtime Specification
## AI Agent Constructor — Draft v0.1

> Статус: архитектурный draft  
> Назначение: описать исполняющую среду AI Agent Constructor, которая превращает определения Agent / Skill / Action / Tool в работающего агента.  
> Главная идея: **Runtime исполняет декларативное поведение агента. Он принимает Events, запускает и возобновляет Skill Runs, исполняет Actions через Tools и сохраняет состояние выполнения.**  
> Соответствие кода: [RUNTIME_IMPLEMENTATION_STATUS.md](./RUNTIME_IMPLEMENTATION_STATUS.md)  
> Согласование с architecture: [ARCHITECTURE_DOCS_ALIGNMENT.md](./ARCHITECTURE_DOCS_ALIGNMENT.md)

---

# 1. Что такое Runtime

Runtime — это исполняющая среда конструктора.

Если Builder отвечает на вопрос:

> «Как должен вести себя агент?»

то Runtime отвечает:

> «Как сделать так, чтобы это поведение реально выполнялось надёжно?»

Runtime работает с опубликованными Definition:

```text
Agent Definition
Skill Definition
Action Definition
Tool Definition
```

и исполняет их:

```text
Event
 ↓
Skill Run
 ↓
FSM
 ↓
Action
 ↓
Tool
 ↓
Result
 ↓
FSM
```

---

# 2. Границы Runtime

Runtime отвечает за:

- запуск Skill Runs;
- хранение текущего состояния Skill Run;
- получение и маршрутизацию Events;
- интерпретацию FSM;
- запуск Actions;
- запуск Tool Commands;
- ожидание внешних Events;
- возобновление suspended Skill Runs;
- retry / timeout на уровне исполнения;
- concurrency;
- cancellation;
- execution history;
- observability;
- version pinning.

Runtime не отвечает за:

- бизнес-логику конкретного домена;
- содержимое Skill;
- реализацию Tools;
- конкретного LLM provider;
- конкретный UI;
- долговременную бизнес-память.

---

# 3. Definition Plane и Runtime Plane

Runtime не изменяет опубликованные Definitions.

Разделяются:

### Definition Plane

```text
Agent
Skill
Action
Tool
Version
```

### Runtime Plane

```text
SkillRun
ActionRun
ToolExecution
Event
State
Variables
```

Например:

```text
Skill:
    process_request@1.3.0
```

и:

```text
SkillRun #8492:
    definition = process_request@1.3.0
    state = waiting_for_foreman
```

---

# 4. Immutable Versions

Опубликованная версия Definition не должна изменяться.

Если Skill изменён:

```text
process_request@1.3.0
```

создаётся:

```text
process_request@1.4.0
```

Существующие Skill Runs продолжают выполнять `@1.3.0`, новые Runs используют `@1.4.0`.

---

# 5. Основные Runtime Entities

Минимальные runtime-сущности:

```text
SkillRun
ActionRun
ToolExecution
Event
```

`SkillRun` — конкретное выполнение Skill.  
`ActionRun` — конкретное выполнение Action внутри SkillRun.  
`ToolExecution` — конкретный вызов Command конкретного Tool.  
`Event` — факт, обрабатываемый Runtime.

---

# 6. SkillRun

Пример:

```json
{
  "id": "run_8291",
  "skill_id": "procurement.process_request",
  "skill_version": "1.4.0",
  "state": "waiting_for_foreman",
  "status": "waiting",
  "params": {
    "request_id": "req_123"
  },
  "variables": {
    "clarification_attempts": 1
  }
}
```

SkillRun должен хранить минимум:

```text
id
skill_id
skill_version
current_state
status
params
variables
created_at
updated_at
correlation
```

---

# 7. SkillRun Status

Минимальный lifecycle:

```text
CREATED
   ↓
RUNNING
   ↓
WAITING
   ↓
RUNNING
   ↓
COMPLETED
```

Также:

```text
FAILED
CANCELLED
```

---

# 8. Durable SkillRun

SkillRun должен быть durable. После значимого изменения состояния Runtime должен иметь возможность восстановить Run после рестарта.

```text
Runtime restart
 ↓
load SkillRun
 ↓
restore state
 ↓
continue when Event arrives
```

---

# 9. FSM Engine

FSM Engine получает:

```text
Skill Definition
SkillRun
Event
```

и определяет:

```text
matching handler
Guard result
Actions
Next State
```

FSM Engine не вызывает Tools.

Концептуально:

```python
transition = fsm.evaluate(
    definition=skill,
    state=run.state,
    event=event
)
```

Результат:

```text
actions:
  parse_request

next_state:
  analyzing
```

---

# 10. FSM Execution

При получении Event Runtime концептуально:

```text
1. Загружает SkillRun.
2. Загружает pinned Skill Definition.
3. Определяет current state.
4. Ищет handlers для Event.
5. Вычисляет Guards.
6. Определяет выбранный handler.
7. Получает Actions.
8. Выполняет Actions.
9. Обновляет State.
10. Выполняет on_enter нового State.
11. Сохраняет Run.
```

Точные transactional guarantees относятся к persistence layer.

---

# 11. Action Execution

FSM говорит:

```text
execute: parse_request
```

Runtime загружает `parse_request@version` и создаёт ActionRun.

Затем выполняется Recipe:

```text
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

Action Executor не меняет Skill State самостоятельно.

---

# 12. ActionRun

Минимальная модель:

```text
ActionRun
├── id
├── action_id
├── action_version
├── skill_run_id
├── status
├── input
├── output
├── current_step
├── error
├── started_at
└── finished_at
```

Lifecycle:

```text
CREATED
 ↓
RUNNING
 ↓
COMPLETED
```

или:

```text
FAILED
CANCELLED
WAITING
```

---

# 13. Tool Execution

Action step, например `memory.search`, создаёт ToolExecution.

Runtime передаёт Tool:

```text
tool_id
command
input
execution context
```

Tool возвращает `result` или `error`.

Runtime сохраняет execution record и продолжает Recipe.

---

# 14. Action Result

После завершения Recipe формируется Action Result.

Например:

```json
{
  "confidence": 0.91,
  "missing_fields": []
}
```

FSM может использовать результат в Guards:

```yaml
on:
  action.parse_request.completed:

    - guard: "result.confidence >= 0.9"
      to: ready

    - guard: "result.confidence < 0.9"
      actions:
        - clarify_with_foreman
      to: waiting_for_foreman
```

---

# 15. Event Routing

Event Router получает Event и ищет Skill Runs, которые могут его обработать **в текущем состоянии**, либо стартует новый run.

Учитываются:

```text
event.type
correlation (skill_run_id, затем сущность / разговор)
current_state — есть ли переход на этот event.type
Skill definition
```

`conversation_id` — адрес голоса (куда ответить), **не** ключ «этот run владеет сессией». См. [INTERACTION_SPEC](./INTERACTION_SPEC_v0.1.md) R0, R4.2.

Resume waiting/running run по `conversation_id` (или `request_id` / `entity_id`) **только если** текущее состояние этого run объявляет переход на данный `event.type`. Иначе waiting не перехватывает событие: резолвится другой скилл / новый run.

Явный `skill_run_id` на событии (completion action, targeted resume) по-прежнему адресует тот run.

Guard остаётся логикой FSM (проверяется при apply, не обязан дублироваться на pin).

Нет перехода на доменный event ≠ перевод run в `error`. No-match **пропускается**, run остаётся в прежнем статусе.

```text
Event
 ↓
явный skill_run_id? → тот run
 ↓
waiting runs по correlation, у которых current_state ждёт event.type
 ↓
иначе новые Skill Runs (initial-state / default / skillId-подсказка)
 ↓
FSM handlers
```

---

# 16. Event Delivery

Базовая модель v0.1:

> **At-least-once delivery**

Одно событие потенциально может быть доставлено более одного раза. Поэтому обработка должна быть idempotent.

---

# 17. Event Deduplication

Минимальный ключ:

```text
event_id
```

Повторная доставка одного `event_id` не должна повторно выполнять side effects.

---

# 18. Event Ordering

Глобальный порядок Events не гарантируется.

Ordering и correlation lock обеспечиваются внутри ключа **работы или сущности**, не всего разговора:

```text
skill_run_id
entity_id
```

`conversation_id` можно использовать для упорядочивания реплик голоса, но **не** как exclusive lock на все работы нити. Несколько Skill Run с одним `conversation_id` — норма ([INTERACTION](./INTERACTION_SPEC_v0.1.md) R5.1).

Код worker (фаза 2): ключ `conv-skill:{conversation_id}:{skill_id}`, когда оба известны — и для inbound, и для completion. Разные скиллы на одной нити не делят lock; два события одного скилла сериализуются (чтобы не форкнуть второй `razgovor` и не гонять completion против следующей реплики). Без skill id: `run:{skill_run_id}` / сущность / `event:{id}`.

Разные correlation domains могут обрабатываться параллельно.

---

# 19. Waiting / Suspension

Если Skill достигает состояния без автоматического продолжения (не final):

```text
WAITING_FOR_FOREMAN
IDLE
```

Runtime:

```text
1. сохраняет State;
2. сохраняет Variables;
3. ставит SkillRun = WAITING;
4. освобождает worker;
5. ждёт Event, для которого **текущее состояние** имеет переход.
```

WAITING не означает «любое событие с тем же `conversation_id` — моё».

Worker не должен удерживаться в ожидании часами.

---

# 20. Resume

При получении Event:

```text
Event
 ↓
явный skill_run_id или waiting run, чьё current_state ждёт event.type
 ↓
SkillRun
 ↓
restore
 ↓
FSM
 ↓
continue
```

Если ни один waiting run не ждёт этот `event.type` — это не resume, а routing нового run (RUNTIME §15).

SkillRun при успешном resume переходит:

```text
WAITING → RUNNING
```

---

# 21. Timers

Timer является источником Event.

Например:

```text
timer.elapsed
```

Scheduler создаёт Event:

```json
{
  "type": "timer.elapsed",
  "payload": {
    "timer": "supplier_followup"
  }
}
```

FSM обрабатывает его как обычный Event.

---

# 22. Concurrency

Runtime поддерживает одновременно множество Skill Runs:

```text
SkillRun #1
SkillRun #2
SkillRun #3
...
```

Несколько run **могут разделять** один `conversation_id` (чат + поручение на одном столе). Они независимы по:

```text
state
variables
ActionRuns
skill_run_id
```

Shared mutable state (мир / стол) не должен изменяться без явной synchronization policy.

Код worker сериализует inbound одного скилла на нити (`conv-skill:{conversation}:{skill}`), не весь разговор. Разные скиллы на одном `conversation_id` не делят lock. Два run одного скилла на одной нити обрабатываются по очереди.

---

# 23. Optimistic Concurrency

Для предотвращения двойной обработки одного SkillRun рекомендуется использовать `version` / `revision`.

Пример:

```text
revision = 17
```

Update допускается только если текущая revision всё ещё 17, после чего становится 18.

---

# 24. Action Concurrency

Независимые Tool calls внутри Recipe могут выполняться параллельно:

```text
       A
   ┌───┼───┐
   B   C   D
   └───┼───┘
       E
```

Runtime должен дождаться завершения parallel group перед продолжением.

---

# 25. Failure Handling

Ошибка Action не обязательно означает Failure SkillRun.

Возможная стратегия:

```text
Action failed
   ↓
retry
   ↓
alternative action
   ↓
human escalation
   ↓
skill failed
```

Skill определяет бизнес-поведение, Runtime обеспечивает технические механизмы исполнения.

---

# 26. Retry

Разделяются:

### Tool retry

Transient ошибки конкретного Tool.

### Action retry

Повтор целого Action.

### Skill-level recovery

Переход в другое State:

```text
SUPPLIER_UNAVAILABLE
 ↓
FIND_ALTERNATIVE_SUPPLIER
```

Эти уровни не следует смешивать.

---

# 27. Timeout

Timeout может применяться к:

```text
ToolExecution
ActionRun
SkillRun
```

Пример:

```text
Tool timeout:   30 sec
Action timeout: 2 min
Skill timeout:  3 days
```

---

# 28. Cancellation

Runtime должен поддерживать отмену:

```text
cancel SkillRun
cancel ActionRun
cancel ToolExecution
```

Внешний side effect после cancellation может потребовать compensation. Полная compensation model остаётся открытой.

---

# 29. Side Effects

Tool Commands могут иметь side effects:

```text
send_message
create_order
update_crm
upload_file
```

Runtime должен знать, что повтор некоторых Commands может быть небезопасен без idempotency.

Tool Command может объявлять:

```yaml
execution:
  idempotent: false
```

или:

```yaml
execution:
  idempotent: true
```

---

# 30. Transaction Boundaries

Не предполагается распределённая ACID-транзакция через несколько внешних систем.

Например:

```text
Telegram
+
CRM
+
Saby
```

не образуют одну транзакцию.

В будущем могут применяться:

```text
outbox
idempotency
saga
compensation
```

---

# 31. Persistence

Минимально нужны записи:

```text
agents
skills
actions
tools

skill_runs
action_runs
tool_executions

events
```

Конкретная БД не является частью Runtime contract. Для первой реализации предполагается PostgreSQL.

---

# 32. Event Persistence

Важные Domain Events желательно сохранять.

Это даёт:

```text
audit
debugging
replay
reflection
analytics
```

Runtime должен различать:

```text
Event stored
Event delivered
Event processed
```

---

# 33. Execution History

Runtime автоматически формирует историю:

```text
Event received
↓
Skill state changed
↓
Action started
↓
Tool executed
↓
Action completed
↓
Skill state changed
```

История должна иметь correlation / causation chain:

```text
evt_100
  ↓
skill_run_42
  ↓
action_run_88
  ↓
tool_exec_991
  ↓
evt_101
```

---

# 34. Observability

Runtime должен поддерживать:

```text
logs
metrics
traces
execution timeline
```

Минимальные категории:

```text
skill_run.started
skill_run.completed
skill_run.failed

action_run.started
action_run.completed
action_run.failed

tool.execution.started
tool.execution.completed
tool.execution.failed

event.published
event.processed
event.failed
```

---

# 35. Context

Runtime не обязан строить полный Context.

Action может использовать:

```text
context.build
```

через Context Tool.

Runtime передаёт Action execution context:

```text
agent_id
skill_run_id
action_run_id
event_id
```

---

# 36. Memory

Memory является Tool.

Runtime не знает, используется ли:

```text
vector
graph
SQL
hybrid
```

Action вызывает, например:

```text
memory.search
memory.store
```

---

# 37. LLM

LLM также является Tool.

Runtime не зависит от конкретного provider:

```text
OpenAI
Anthropic
Ollama
Mistral
```

Action использует абстрактный интерфейс:

```text
llm.run
llm.run_structured
```

---

# 38. Human Events

Human interaction является частью Event model.

Например:

```text
human.request.approved
human.request.rejected
human.request.corrected
human.shipment.confirmed
```

Для Runtime это обычные Events.

---

# 39. Runtime API

Минимальный внутренний API:

```text
publish_event(event)

start_skill(
    skill_id,
    version,
    params
)

resume_skill(
    skill_run_id,
    event
)

cancel_skill(
    skill_run_id
)

get_skill_run(
    skill_run_id
)

execute_action(
    action_id,
    version,
    input
)
```

Это концептуальный API; транспорт не фиксируется.

---

# 40. Runtime Commands vs Domain Events

Runtime может иметь команды управления:

```text
start_skill
cancel_skill
retry_action
```

Это не Events.

Command:

> Выполни операцию.

Event:

> Операция/факт уже произошли.

Например:

```text
cancel_skill
```

может привести к:

```text
skill.run.cancelled
```

---

# 41. Agent Wake-up

Runtime должен уметь определить, нужно ли Event разбудить конкретный SkillRun.

Например:

```text
supplier.reply.received
```

correlates with:

```text
SkillRun #42
state = waiting_for_supplier
```

Runtime загружает Run и передаёт Event FSM.

---

# 42. Multiple matching Skill Runs

Один Event может соответствовать нескольким Skill Runs.

Например:

```text
invoice.received
```

может интересовать:

```text
process_invoice #1
shipment_tracking #2
accounting_notification #3
```

Каждый Run получает независимую execution context.

---

# 43. Replay

Runtime должен быть архитектурно совместим с replay:

```text
Stored Event
 ↓
Replay
 ↓
FSM
```

Replay требует idempotency и совместимости версий.

В v0.1 полноценный UI replay не обязателен.

---

# 44. Recovery

Если worker падает во время исполнения:

```text
worker crash
 ↓
unfinished ActionRun
 ↓
runtime recovery
```

Runtime должен определить:

```text
completed?
in-progress?
retryable?
unknown external side effect?
```

Особенно опасен случай:

```text
Tool completed externally
но Runtime не получил response
```

Поэтому idempotency и execution identifiers обязательны для side-effecting Tools.

---

# 45. Runtime Boundaries

Runtime не должен становиться «умным агентом».

Он не должен:

- решать бизнес-задачи;
- сам выбирать поставщика;
- сам придумывать сообщения;
- сам изменять Memory;
- использовать LLM без Action;
- обходить FSM;
- напрямую обращаться к CRM;
- содержать domain-specific rules.

Runtime — исполнитель.

---

# 46. Core Runtime Components

На уровне реализации могут существовать:

```text
Runtime
├── Event Dispatcher
├── Skill Runner
├── FSM Interpreter
├── Action Executor
├── Tool Executor
├── Scheduler
├── Persistence
├── Locking / Concurrency
└── Observability
```

Это implementation architecture, а не сущности DSL.

---

# 47. Минимальный execution loop

Упрощённо:

```python
async def handle_event(event):

    runs = router.find_matching_runs(event)

    for run in runs:

        run = repository.lock(run.id)

        transition = fsm.evaluate(
            skill=run.skill_definition,
            state=run.state,
            event=event,
        )

        for action in transition.actions:
            await action_executor.execute(
                action=action,
                run=run,
                event=event,
            )

        run.state = transition.next_state

        await repository.save(run)
```

Это упрощённая модель. Реальная реализация должна учитывать transactions, retries, idempotency и recovery.

---

# 48. Acceptance Criteria

Runtime v0.1 считается рабочим, если он способен:

```text
1. запускать Skill;
2. хранить SkillRun;
3. интерпретировать FSM;
4. принимать Event;
5. выполнять Actions;
6. выполнять Tool Commands;
7. сохранять Action/Tool executions;
8. приостанавливать Skill;
9. возобновлять Skill по Event;
10. переживать restart;
11. предотвращать двойную обработку Event;
12. выполнять несколько Skill Runs параллельно;
13. поддерживать retry;
14. поддерживать timeout;
15. поддерживать cancellation;
16. вести execution history.
```

---

# 49. Открытые вопросы

Оставляем для следующих версий:

1. Точный event bus protocol.
2. Outbox pattern.
3. Политика distributed locking.
4. Полноценный scheduler.
5. Exactly-once semantics.
6. Saga / compensation.
7. Parallel branches внутри Skill.
8. Composite Skills.
9. Dynamic Skill creation.
10. Dynamic Action selection.
11. Planner.
12. Replay semantics.
13. Deterministic replay.
14. Distributed execution.
15. Multi-tenant isolation.
16. Sandboxing Tools.
17. Resource quotas.
18. Tool placement на разных workers.
19. Streaming.
20. Priority scheduling.

---

# 50. Главная архитектурная формула

```text
                        EVENT
                          │
                          ▼
                    EVENT ROUTING
                          │
                          ▼
                      SKILL RUN
                          │
                          ▼
                         FSM
                          │
                    State + Event
                          │
                          ▼
                       ACTION
                          │
                          ▼
                    TOOL COMMAND
                          │
                          ▼
                   EXTERNAL WORLD
                          │
                          ▼
                        EVENT
```

И четыре центральные сущности DSL:

```text
Tool   = capability
Action = operation
Skill  = process
Agent  = composition
```

FSM:

```text
Skill = FSM(State + Event → Actions)
```

Runtime:

```text
Runtime = execution of Definitions + persistence + event processing
```

---

# 51. Главный принцип

> **Конструктор описывает поведение. Runtime исполняет поведение.**

Builder создаёт:

```text
Agent
Skills
Actions
Tools
```

Runtime обеспечивает:

```text
Events
State
Execution
Waiting
Recovery
Concurrency
Observability
```

Runtime не должен становиться ещё одним «умным агентом». Его сила — в том, что он предсказуемо и надёжно исполняет созданную человеком модель поведения агента.
