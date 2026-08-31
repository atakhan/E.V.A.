# Action Specification
## AI Agent Constructor — Draft v0.1

> Статус: архитектурный draft. Назначение: определить контракт между Skill/FSM и Tools.

---

# 1. Что такое Action

**Action = атомарная операция агента.**

Action отвечает на вопрос:

> **Что агент делает в рамках текущего процесса?**

Примеры:

```text
ingest_channel_message
parse_request
clarify_with_foreman
propose_normalization
learn_from_correction
show_tmc_alternatives
request_supplier_quote
process_supplier_reply
request_invoice
```

Action не является Skill.

```text
Action = операция
Skill  = процесс
```

Skill использует Actions в своей FSM.

---

# 2. Граница между Tool, Action и Skill

### Tool

> Что агент умеет делать.

Примеры:

```text
telegram.send_message
memory.search
crm.update
llm.run_structured
```

### Action

> Что агент делает.

Пример:

```text
clarify_with_foreman
```

может использовать:

```text
llm.run
telegram.send_message
crm.transition
```

### Skill

> Как агент решает определённый класс задач.

Пример:

```text
process_foreman_request
```

может содержать:

```text
NEW
 ↓
ANALYZING
 ↓
CLARIFYING
 ↓
WAITING_FOR_FOREMAN
 ↓
READY
```

и вызывать:

```text
parse_request
clarify_with_foreman
propose_normalization
```

---

# 3. Главное свойство Action

Action должен скрывать детали реализации от FSM.

FSM:

```yaml
on:
  request.received:
    actions:
      - parse_request
    to: analyzing
```

не должна знать, что `parse_request` внутри вызывает:

```text
context.build
memory.search
catalog.search_tmc
llm.run_structured
crm.update
```

Таким образом:

```text
FSM
 ↓
Action
 ↓
Recipe
 ↓
Tools
```

---

# 4. Action как Recipe

Action содержит декларативный рецепт исполнения.

Пример:

```yaml
id: parse_request
version: "1.0.0"

description: "Parse incoming foreman request"

policy: auto

input_schema: ParseRequestInput
output_schema: ParsedRequestV1

recipe:

  - id: build_context
    tool: context
    command: build

  - id: search_memory
    tool: memory
    command: search

  - id: search_catalog
    tool: catalog
    command: search_tmc

  - id: analyze
    tool: llm
    command: run_structured

  - id: update_request
    tool: crm
    command: update
```

Recipe определяет, как получить результат Action из доступных Tool Commands.

---

# 5. Структура Action

Минимально:

```text
Action
├── id
├── version
├── description
├── policy
├── input schema
├── output schema
└── recipe
```

Опционально могут появляться:

```text
├── permissions
├── timeout
├── retry policy
├── idempotency
├── compensation
└── metadata
```

Не следует добавлять эти поля без необходимости в v0.1.

---

# 6. Action ID

Action ID должен быть:

- уникальным;
- стабильным;
- пригодным для DSL;
- независимым от конкретного Skill.

Примеры:

```text
parse_request
clarify_with_foreman
request_supplier_quote
process_supplier_reply
request_invoice
learn_from_correction
```

Action может использоваться несколькими Skills.

---

# 7. Versioning

Action использует SemVer:

```text
MAJOR.MINOR.PATCH
```

Например:

```text
parse_request@1.2.0
```

Если меняется input/output contract несовместимым образом, требуется MAJOR version.

Skill должен ссылаться на совместимую версию Action.

---

# 8. Input Schema

Action получает структурированный input.

Пример:

```yaml
input_schema:
  type: object

  required:
    - request_id

  properties:

    request_id:
      type: string

    message_id:
      type: string
```

Input может приходить из:

```text
Skill parameters
Event payload
Previous Action result
Variables
Context
```

---

# 9. Output Schema

Action должен возвращать структурированный результат.

Пример:

```yaml
output_schema:
  type: object

  properties:

    items:
      type: array

    confidence:
      type: number

    missing_fields:
      type: array
```

Результат Action может:

- использоваться следующими Actions;
- использоваться Guards FSM;
- сохраняться в Skill Run;
- порождать Domain Event.

---

# 10. Recipe Steps

Recipe состоит из последовательности Tool Commands.

Пример:

```yaml
recipe:

  - id: context
    tool: context
    command: build

  - id: memory
    tool: memory
    command: search

  - id: llm
    tool: llm
    command: run_structured

  - id: crm
    tool: crm
    command: update
```

Каждый Step должен иметь уникальный локальный ID.

---

# 11. Передача данных между Steps

Step должен иметь возможность ссылаться на:

```text
Action input
Event
Skill parameters
previous step results
runtime variables
context
```

Пример:

```yaml
- id: search_memory
  tool: memory
  command: search

  input:
    query: "{{input.raw_text}}"
```

Следующий Step:

```yaml
- id: analyze
  tool: llm
  command: run_structured

  input:
    context: "{{steps.context.result}}"
    memories: "{{steps.search_memory.result}}"
```

Это превращает Recipe в небольшой декларативный execution graph.

---

# 12. Sequential execution

По умолчанию Steps выполняются последовательно:

```text
A
 ↓
B
 ↓
C
```

---

# 13. Parallel execution

Recipe может объявлять независимые Steps как параллельные.

Например:

```text
search suppliers
      ├── CRM
      ├── history
      └── web
```

После завершения группы результат может использовать следующий Step.

Параллельность является возможностью runtime, а не обязательной характеристикой Action.

---

# 14. Conditions внутри Recipe

Action может иметь условное выполнение Step.

Пример:

```yaml
- id: search_web
  when: "steps.crm.result.count == 0"

  tool: web
  command: search_suppliers
```

Однако сложную бизнес-логику предпочтительно держать в Skill FSM.

Принцип:

> **Recipe conditions — локальная техническая логика Action.**

> **FSM guards — логика перехода процесса.**

---

# 15. Action Result как граница

После завершения Recipe Action возвращает один итоговый результат:

```text
Recipe
 ↓
Action Result
```

FSM не должна видеть внутренние Tool executions Action.

Например FSM знает:

```text
action.parse_request.completed
```

и результат:

```json
{
  "confidence": 0.91,
  "missing_fields": []
}
```

Но ей не нужно знать:

```text
memory.search completed
catalog.search completed
llm completed
crm.update completed
```

---

# 16. Action Errors

Action может завершиться:

```text
success
failed
cancelled
timeout
```

Ошибка должна быть структурированной:

```json
{
  "code": "CATALOG_UNAVAILABLE",
  "message": "Catalog service unavailable",
  "retryable": true,
  "step": "search_catalog"
}
```

---

# 17. Retry

Retry возможен на двух уровнях.

### Tool level

Tool сообщает, является ли ошибка retryable.

### Action level

Action может задать ограничение:

```yaml
retry:
  max_attempts: 3
```

Action не должен самостоятельно реализовывать retry loop.

---

# 18. Idempotency

Side-effect Actions должны поддерживать возможность безопасного повторного исполнения.

Примеры:

```text
send_message
create_order
send_invoice
```

могут использовать:

```text
idempotency_key
```

---

# 19. Policy

Action может объявлять policy.

Базовые значения:

```text
auto
needs_human
```

Например:

```yaml
id: parse_request
policy: auto
```

и:

```yaml
id: batch_confirm_requests
policy: needs_human
```

В будущем возможны более детальные уровни автономности.

---

# 20. Permissions

Action может требовать permissions:

```yaml
permissions:
  - crm.request.write
  - telegram.messages.send
```

Runtime проверяет права до выполнения Recipe.

Tool Commands также могут иметь собственные permissions.

---

# 21. Human Gate

Если Action требует человека:

```text
Action
  ↓
human gate
  ↓
approval
  ↓
Recipe execution
```

Например `batch_confirm_requests` может собрать кандидатов, показать их пользователю, дождаться подтверждения и выполнить изменения.

Human Gate является runtime capability.

---

# 22. Async Action

Action может вернуть состояние ожидания и execution id.

```text
Action
 ↓
execution_id
 ↓
waiting
 ↓
Event
 ↓
Runtime resumes
```

Но длительное ожидание часов или дней относится к Skill Run, а не к Action Executor.

---

# 23. Action и Events

Action может породить Domain Events через Tool или runtime.

Например:

```text
crm.create
    ↓
crm.request.created
```

Техническое:

```text
action.completed
```

необходимо для runtime, observability и истории.

Бизнес-событие:

```text
crm.request.created
```

может использоваться FSM.

---

# 24. Action Composition

В v0.1 предпочтительно не делать прямую композицию:

```text
Action
 ↓
Action
 ↓
Action
```

Если нужна композиция процессов, использовать Skill:

```text
Skill
 ↓
Action
 ↓
Action
 ↓
Action
```

Так сохраняется понятная граница атомарности.

---

# 25. Spawn / Batch

Массовые операции лучше строить через Skill Runs.

Например:

```text
Action: discover_requests
        ↓
Skill Run #1
Skill Run #2
Skill Run #3
...
```

Action обнаруживает объекты и запускает нужное количество экземпляров Skill.

---

# 26. Action не должен управлять FSM

Action возвращает результат, но не выбирает следующий State.

Правильно:

```text
Action
 ↓
Result
 ↓
FSM
 ↓
Guard
 ↓
Next State
```

Неправильно:

```text
Action
 ↓
fsm.transition(...)
```

---

# 27. Context внутри Action

Action может использовать Context Tool:

```text
context.build
```

Но Context не должен быть обязательной частью каждого Action.

---

# 28. Пример: parse_request

```yaml
id: parse_request
version: "1.0.0"

description: "Parse a foreman message into normalized request items"

policy: auto

input_schema:
  type: object
  required:
    - request_id
    - message

output_schema:
  type: object
  properties:
    items:
      type: array
    confidence:
      type: number
    missing_fields:
      type: array

recipe:

  - id: context
    tool: context
    command: build
    input:
      recipe: foreman_request_v1

  - id: memory
    tool: memory
    command: search
    input:
      query: "{{input.message}}"

  - id: catalog
    tool: catalog
    command: search_tmc
    input:
      query: "{{input.message}}"

  - id: llm
    tool: llm
    command: run_structured
    input:
      prompt: parse_foreman_request
      context:
        base: "{{steps.context.result}}"
        memory: "{{steps.memory.result}}"
        catalog: "{{steps.catalog.result}}"
      schema: ParsedRequestV1

  - id: update
    tool: crm
    command: request.update
    input:
      request_id: "{{input.request_id}}"
      data: "{{steps.llm.result}}"
```

---

# 29. Пример: clarify_with_foreman

```yaml
id: clarify_with_foreman
version: "1.0.0"

description: "Ask the foreman for missing information"

policy: auto

input_schema:
  type: object
  required:
    - request_id
    - conversation_id
    - missing_fields

output_schema:
  type: object
  properties:
    message_id:
      type: string

recipe:

  - id: context
    tool: context
    command: build
    input:
      scope: request

  - id: draft
    tool: llm
    command: run
    input:
      prompt: draft_clarification
      context: "{{steps.context.result}}"
      missing_fields: "{{input.missing_fields}}"

  - id: send
    tool: telegram
    command: send_message
    input:
      chat_id: "{{input.conversation_id}}"
      text: "{{steps.draft.result.text}}"
```

FSM затем может перейти в:

```text
CLARIFYING
 ↓
WAITING_FOR_FOREMAN
```

Action сам переход не делает.

---

# 30. Action Run

Для каждого исполнения Action создаётся runtime-сущность:

```text
ActionRun
├── id
├── action_id
├── action_version
├── skill_run_id
├── input
├── status
├── current_step
├── output
├── error
├── started_at
└── finished_at
```

Это runtime persistence, а не часть DSL Action Definition.

---

# 31. Action Recipe как execution graph

Базовая форма может быть последовательной:

```text
A → B → C
```

Но архитектура должна допускать DAG:

```text
      A
   ┌──┴──┐
   B     C
   └──┬──┘
      D
```

При этом сложную ветвящуюся бизнес-логику следует по возможности помещать в Skill FSM.

```text
Skill FSM
 = business/process control

Action Recipe
 = operation implementation
```

---

# 32. Критический принцип разделения ответственности

```text
Skill:
"Когда это произошло и какое действие нужно выполнить?"

Action:
"Что именно мы выполняем?"

Tool:
"Каким механизмом это сделать?"

Runtime:
"Как физически это исполнить надёжно?"
```

---

# 33. Acceptance Criteria для Action SDK v0.1

Модель считается рабочей, если можно декларативно описать:

```text
ingest_channel_message
parse_request
clarify_with_foreman
propose_normalization
learn_from_correction
show_tmc_alternatives
request_supplier_quote
process_supplier_reply
request_invoice
process_invoice
```

без прямого обращения из Action к:

```text
Telegram API
CRM SDK
OpenAI SDK
Postgres
Redis
```

Action должен видеть только:

```text
Tool
Command
Schema
Input
Output
```

---

# 34. Открытые вопросы

Остаются для следующих версий:

1. Полноценный DAG вместо последовательного Recipe.
2. Циклы внутри Recipe.
3. Action → Action composition.
4. Transactions / compensation.
5. Streaming results.
6. Human Gate внутри Recipe.
7. Dynamic Tool selection.
8. LLM-driven Action selection.
9. Typed expressions для `when` и guards.
10. Secrets / credential references внутри Recipe.
11. Remote Actions.
12. Action marketplace.
13. Сложная retry / timeout policy.
14. Compensation actions / rollback.
15. Формальная модель transactional side effects.

---

# 35. Итоговая модель

```text
                         AGENT
                           │
                         SKILL
                           │
                           ▼
                          FSM
                     ┌─────┴─────┐
                     │           │
                   STATE        EVENT
                     │           │
                     └─────┬─────┘
                           ▼
                         ACTION
                           │
                     Action Recipe
                           │
                 ┌─────────┼─────────┐
                 ▼         ▼         ▼
               TOOL      TOOL      TOOL
                 │         │         │
                 ▼         ▼         ▼
              external  external  external
                world     world     world
```

Главный runtime-цикл:

```text
Event
  ↓
FSM
  ↓
Action
  ↓
Tool Commands
  ↓
Result
  ↓
FSM
```

**Action — мост между декларативным поведением Skill и конкретными capabilities Tools.**
