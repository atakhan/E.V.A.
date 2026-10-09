# Event Specification
## AI Agent Constructor — Draft v0.1

> Статус: архитектурный draft  
> Назначение: определить универсальную модель событий между Tools, Runtime и Skill/FSM.  
> Основная идея: **Event — это факт, который произошёл; Event не является командой и не является указанием, что делать.**

---

# 1. Что такое Event

**Event = факт произошедшего события.**

Event отвечает на вопрос:

> **Что произошло?**

Примеры:

```text
channel.message.received
supplier.reply.received
invoice.received
human.reviewed
request.created
shipment.updated
```

Event не отвечает на вопрос:

> Что теперь делать?

Это решает FSM / Skill Runtime.

Основной цикл:

```text
Event
  ↓
FSM
  ↓
Action
  ↓
Tools
  ↓
World
  ↓
Event
```

---

# 2. Event vs Command vs Result

Это три разные сущности.

### Command

Намерение выполнить операцию:

```text
telegram.send_message
crm.request.update
memory.search
```

Command говорит:

> Сделай X.

### Event

Факт:

```text
telegram.message.received
crm.request.updated
supplier.reply.received
```

Event говорит:

> X произошло.

### Result

Результат конкретного execution:

```text
action.parse_request.completed
memory.search.result
tool.execution.failed
```

Result говорит:

> Операция X завершилась вот с таким результатом.

---

# 3. Где возникают Events

Event может возникнуть:

1. во внешнем мире;
2. внутри Tool;
3. в результате изменения бизнес-данных;
4. вследствие действия человека;
5. в результате системного таймера;
6. как результат runtime execution.

Примеры:

```text
Telegram
    ↓
channel.message.received

CRM
    ↓
crm.request.updated

Human
    ↓
human.request.approved

Scheduler
    ↓
timer.elapsed
```

---

# 4. Event Source

Каждый Event должен иметь источник:

```text
source
```

Примеры:

```text
telegram
crm
saby
scheduler
human
runtime
system
```

Source помогает:

- трассировать происхождение Event;
- маршрутизировать;
- диагностировать;
- контролировать доверие к источнику.

---

# 5. Event Type

Event Type является стабильным идентификатором семантики события.

Рекомендуемый формат:

```text
<domain>.<entity>.<event>
```

Примеры:

```text
channel.message.received
crm.request.created
crm.request.updated
supplier.reply.received
invoice.received
human.reviewed
```

Event Type должен быть:

- уникальным;
- стабильным;
- понятным;
- версионируемым при изменении schema.

---

# 6. Event Schema

Каждый Event Type имеет payload schema.

Рекомендуемый формат:

```text
JSON Schema
```

Пример:

```yaml
type: object

required:
  - message_id
  - conversation_id
  - sender_id
  - text

properties:

  message_id:
    type: string

  conversation_id:
    type: string

  sender_id:
    type: string

  text:
    type: string
```

Schema является частью Event contract.

---

# 7. Event Envelope

Рекомендуемая структура:

```json
{
  "id": "evt_123",

  "type": "channel.message.received",

  "version": "1.0",

  "source": "telegram",

  "timestamp": "2026-08-27T18:00:00Z",

  "correlation": {
    "conversation_id": "conv_123"
  },

  "payload": {
    "message_id": "456",
    "sender_id": "user_42",
    "text": "Нужны грибки 10x100"
  },

  "metadata": {
    "focus": {
      "view": "requests",
      "openEntityId": "REQ-17",
      "selectedEntityIds": ["REQ-17"]
    }
  }
}
```

---

# 8. Event ID

Каждый Event должен иметь глобально уникальный:

```text
event_id
```

Event ID используется для:

- дедупликации;
- трассировки;
- аудита;
- поиска;
- повторной доставки.

Event ID не должен меняться при retry доставки.

---

# 9. Event timestamp

Event содержит:

```text
timestamp
```

который означает время фактического возникновения события, а не время его обработки runtime.

При необходимости Runtime может хранить отдельно:

```text
received_at
processed_at
```

---

# 10. Correlation

Correlation связывает Event с контекстом выполнения.

Минимально могут использоваться:

```text
conversation_id   # нить голоса (web sessionId). Не владелец Skill Run.
entity_id
skill_run_id      # конкретная работа
action_run_id
agent_id
request_id
user_id           # актёр (веб-контракт actor_id → сюда)
parent_run_id
```

Пример:

```json
{
  "correlation": {
    "conversation_id": "conv_123",
    "request_id": "req_42",
    "skill_run_id": "run_991",
    "user_id": "user_42"
  }
}
```

Не каждое поле обязательно.

**Разговор ≠ работа.** Одному `conversation_id` могут соответствовать несколько `skill_run_id`. Waiting-run не имеет права трактовать любое событие этой нити как resume. Норма: [INTERACTION_SPEC](./INTERACTION_SPEC_v0.1.md) R0, [RUNTIME §15](./RUNTIME_SPEC_v0.1.md).

**Фокус акта** (`view`, `openEntityId`, `selectedEntityIds`) — не поле correlation «навсегда». Класть в `metadata.focus` или `payload.focus` этого события.

---

# 11. Correlation ≠ Causation

Важно разделять:

### Correlation

К какому контексту относится событие.

```text
request_id = 42
```

### Causation

Какое событие или действие непосредственно стало причиной этого события.

Например:

```json
{
  "causation_id": "evt_100"
}
```

Это позволяет строить causal chain:

```text
evt_100
  ↓
action_42
  ↓
evt_101
  ↓
action_43
  ↓
evt_102
```

Causation является рекомендуемым полем для runtime.

---

# 12. Domain Events и Runtime Events

Это принципиальное разделение.

## Domain Event

Событие, значимое для поведения агента или бизнес-процесса.

Примеры:

```text
channel.message.received
request.created
request.confirmed
supplier.reply.received
invoice.received
human.request.approved
shipment.delivered
```

Такие Events могут использоваться FSM.

## Runtime Event

Техническое событие исполнения:

```text
tool.execution.started
tool.execution.completed
action.execution.failed
skill.run.suspended
```

Они нужны для:

- observability;
- metrics;
- debugging;
- execution history.

Обычно Runtime Events не должны быть частью бизнес-FSM.

---

# 13. Event Lifecycle

Минимальный lifecycle доставки:

```text
CREATED
  ↓
PUBLISHED
  ↓
DELIVERED
  ↓
PROCESSED
```

Возможны:

```text
FAILED
RETRYING
DEAD_LETTER
```

Важно:

> Lifecycle доставки Event не следует путать с бизнес-состоянием самого Event.

Event сам по себе не становится `completed` в бизнес-смысле.

---

# 14. At-least-once delivery

Базовая модель Event Bus в v0.1:

> **at-least-once delivery**

Это означает, что одно событие потенциально может быть доставлено более одного раза.

Поэтому consumers обязаны быть защищены от дубликатов.

Пример:

```text
event_id = evt_123

delivery #1
delivery #2
```

FSM не должна дважды выполнить побочные действия из-за повторной доставки.

---

# 15. Idempotency

Event processing должен поддерживать deduplication.

Runtime может хранить:

```text
processed_events
```

или иметь иной механизм idempotency.

Минимальный ключ:

```text
event_id
```

Для некоторых типов Events может потребоваться дополнительный business idempotency key.

---

# 16. Event Ordering

Не следует предполагать глобальный порядок всех Events системы.

Порядок должен гарантироваться только там, где это действительно необходимо.

Например, для одной:

```text
conversation_id
```

можно требовать:

```text
message.received #1
message.received #2
message.received #3
```

Но Events разных разговоров могут обрабатываться параллельно.

---

# 17. Event Routing

Event Routing является механизмом Runtime.

Event содержит семантику:

```text
channel.message.received
```

Runtime решает:

```text
какие Skill Runs заинтересованы?
```

Схема:

```text
Event
  ↓
Event Router
  ↓
matching Skill Runs
  ↓
FSM
```

Tool не должен знать Event Router.

---

# 18. Event Subscription

Skill должен иметь возможность фактически «слушать» Events через свою FSM.

Например:

```yaml
waiting_for_foreman:

  on:

    channel.message.received:
      - actions:
          - parse_foreman_response

        to: analyzing
```

В этом случае:

```text
subscription
```

определяется не отдельным API Tool, а декларацией Skill FSM.

---

# 19. Event Filtering

Одного Event Type недостаточно.

Например:

```text
channel.message.received
```

может возникать в тысячах чатов.

Skill может использовать correlation и Guards:

```yaml
guard: "event.conversation_id == task.conversation_id"
```

Таким образом:

```text
Event Type
+
Correlation
+
Guard
```

определяют, подходит ли Event конкретному Skill Run.

---

# 20. Event → State

Основная реакция Skill:

```text
Current State
+
Event
+
Guard
→
Actions
+
Next State
```

Пример:

```text
WAITING_FOR_FOREMAN
        │
        │ channel.message.received
        ▼
parse_foreman_response
        │
        ▼
ANALYZING
```

Event сам не меняет State.

Это делает FSM Runtime.

---

# 21. Event → Multiple Skills

Один Event может интересовать несколько Skills (несколько **новых** или уже ждущих этот тип в текущем состоянии). Это не означает «отдать событие единственному waiting-run на том же `conversation_id`». См. RUNTIME §15.

Например:

```text
invoice.received
```

может вызвать:

```text
Skill: process_invoice
Skill: update_shipment_tracking
Skill: accounting_notification
```

Это нормальное поведение.

Events не должны принадлежать одному Skill.

---

# 22. Event Fan-out

Схема:

```text
                 Event
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
       Skill A  Skill B  Skill C
```

Каждый Skill Run получает собственную обработку Event.

Ошибки одного consumer не должны автоматически ломать остальные.

---

# 23. Event Payload

Payload должен содержать минимально достаточную информацию.

Плохо:

```text
channel.message.received
+
вся база компании
+
весь Conversation
+
вся Memory
```

Хорошо:

```text
channel.message.received

{
  message_id,
  conversation_id,
  sender_id,
  content
}
```

Контекст достраивается Context/Tools при необходимости.

Принцип:

> **Event сообщает, что произошло; Context собирает, что нужно знать для реакции.**

---

# 24. Event Snapshot vs Live Data

Event должен содержать данные такими, какими они были в момент события.

Например:

```text
invoice.received
```

может содержать:

```text
invoice_id
supplier_id
received_at
document_id
```

А актуальную информацию по счёту Skill при необходимости получает через CRM Tool.

Таким образом:

```text
Event
= факт

Business Data
= текущее состояние мира
```

---

# 25. Event Versioning

Каждый Event Type должен иметь schema version:

```text
channel.message.received@1
```

Изменение schema, нарушающее совместимость, требует новой major version.

Например:

```text
channel.message.received@1
channel.message.received@2
```

Runtime может поддерживать несколько версий одновременно.

---

# 26. Event Validation

Перед публикацией Event Runtime/Tool должен проверить:

```text
✓ type существует
✓ version известна
✓ payload соответствует schema
✓ event_id существует
✓ timestamp корректен
```

Невалидный Event не должен поступать в FSM.

---

# 27. Event Security

Events могут содержать чувствительные данные.

Поэтому:

- payload должен иметь уровень доступа;
- secrets не должны попадать в Event;
- access control применяется на уровне consumers;
- raw credentials никогда не включаются.

Например нельзя:

```json
{
  "api_key": "..."
}
```

в Event.

---

# 28. Event Persistence

Для важных Domain Events рекомендуется хранение Event в persistent store.

Например:

```text
events
```

с:

```text
event_id
type
version
source
timestamp
correlation
causation
payload
```

Это позволяет:

- audit;
- replay;
- debugging;
- Reflection;
- analysis.

---

# 29. Event Replay

В будущем Runtime может повторно подать исторический Event:

```text
stored Event
      ↓
replay
      ↓
Skill
```

Replay требует строгой идемпотентности и version compatibility.

В v0.1 replay может быть только архитектурной возможностью, без полноценного UI.

---

# 30. Dead Letter

Если Event не удаётся обработать после допустимого количества retries:

```text
Event
 ↓
retry
 ↓
retry
 ↓
failure
 ↓
DEAD_LETTER
```

Dead-lettered Event не должен незаметно исчезать.

Нужен способ:

```text
inspect
retry
discard
```

---

# 31. Event Handler Error

Если Skill не может обработать Event:

```text
Event
 ↓
Skill
 ↓
handler failed
```

это не означает, что Event необходимо удалить.

Runtime должен сохранять failure information.

Политика retry зависит от Runtime/Skill policy.

---

# 32. System Events

Runtime может создавать стандартные системные Events:

```text
timer.elapsed
skill.run.started
skill.run.completed
skill.run.failed
action.completed
action.failed
```

> **Примечание:** generic `action.completed` / `action.failed` — system/observability events.  
> FSM transitions используют **конкретные** типы: `action.<action_id>.completed` и `action.<action_id>.failed` (см. §35).

Но следует внимательно контролировать их использование в FSM.

Например:

```text
timer.elapsed
```

может быть легальным business trigger.

А:

```text
tool.execution.started
```

обычно является observability event.

---

# 33. Timer Events

Ожидание времени может быть выражено через Event:

```text
timer.elapsed
```

Например:

```yaml
waiting_for_supplier:

  on:

    timer.elapsed:

      - guard: "timer.name == 'supplier_followup'"
        actions:
          - follow_up_supplier
        to: contacting_supplier
```

Сам Timer реализуется Runtime/Scheduler.

---

# 34. Human Events

Человек является источником Events так же, как Tool.

Примеры:

```text
human.request.approved
human.request.rejected
human.request.corrected
human.intervention.started
human.shipment.confirmed
```

Это позволяет Human-in-the-loop естественно вписать в одну модель:

```text
External world
   ↓
Event
   ↓
FSM
```

---

# 35. Event Naming

Рекомендуется использовать стабильную и предсказуемую семантику.

Хорошо:

```text
channel.message.received
supplier.reply.received
invoice.received
human.request.approved
action.parse_request.completed
```

Action completion (FSM trigger):

```text
action.<action_id>.completed   # после успешного Action
action.<action_id>.failed      # при ошибке Action
action.completed               # system/observability only — не для FSM
```

Плохо:

```text
something_happened
new_msg
do_the_thing
supplier_ok
```

Event name должен описывать факт, а не команду.

---

# 36. Event Schema Example

```yaml
id: channel.message.received
version: "1.0.0"

payload_schema:

  type: object

  required:
    - message_id
    - conversation_id
    - sender_id
    - content

  properties:

    message_id:
      type: string

    conversation_id:
      type: string

    sender_id:
      type: string

    content:
      type: object

      required:
        - type

      properties:

        type:
          enum:
            - text
            - voice
            - image
            - file

        text:
          type: string
```

---

# 37. Example Event Flow

Сценарий:

```text
Прораб пишет в Telegram
```

### 1. Telegram Tool

Получает сообщение.

### 2. Tool

Публикует:

```text
channel.message.received
```

### 3. Event Router

Находит подходящий Skill Run.

### 4. FSM

Skill находится:

```text
WAITING_FOR_MESSAGE
```

### 5. FSM

Выполняет:

```text
ingest_channel_message
```

### 6. Action

Использует:

```text
context
crm
memory
llm
```

### 7. Action Result

Возвращается в Skill.

### 8. FSM

Переходит:

```text
ANALYZING
```

или:

```text
WAITING_FOR_FOREMAN
```

---

# 38. Event Contract

Минимальный обязательный контракт Event:

```text
Event
├── id
├── type
├── version
├── source
├── timestamp
├── payload
└── correlation
```

Рекомендуется дополнительно:

```text
causation_id
metadata
```

---

# 39. Что Event НЕ должен делать

Event не должен:

- содержать инструкцию для агента;
- напрямую запускать конкретный Action;
- напрямую менять State;
- содержать всю память агента;
- зависеть от конкретного Skill;
- содержать secrets;
- определять способ обработки.

Плохо:

```json
{
  "type": "message.received",
  "action": "parse_request"
}
```

Хорошо:

```json
{
  "type": "channel.message.received"
}
```

А FSM уже решает:

```text
что делать?
```

---

# 40. Что Event ДОЛЖЕН делать

Event должен:

- описывать факт;
- иметь стабильный type;
- иметь schema;
- иметь уникальный ID;
- содержать timestamp;
- иметь достаточную correlation information;
- быть валидируемым;
- поддерживать deduplication;
- быть трассируемым;
- при необходимости сохраняться.

---

# 41. Acceptance Criteria для Event SDK v0.1

Модель считается рабочей, если через неё можно выразить:

```text
channel.message.received
channel.message.sent
supplier.reply.received
request.created
request.updated
invoice.received
human.request.approved
human.request.corrected
shipment.updated
timer.elapsed
```

и Runtime способен:

```text
publish Event
→ route Event
→ deliver Event
→ evaluate FSM
→ execute Actions
→ continue Skill Run
```

без того, чтобы Event зависел от конкретного Tool, Skill или бизнес-процесса.

---

# 42. Открытые вопросы

Для следующих версий остаются:

1. Политика ordering.
2. Partitioning Event Stream.
3. Exact event bus protocol.
4. Replay semantics.
5. Event snapshots.
6. Schema registry.
7. Event retention.
8. Event encryption.
9. Cross-tenant Event isolation.
10. Exactly-once processing, если когда-либо понадобится.
11. Event priority.
12. Delayed Events.
13. Event aggregation/debouncing.
14. Event transactions / outbox pattern.
15. Distributed tracing propagation.

---

# 43. Итоговая модель

Главная формула:

```text
Event = Fact
Command = Intent
Result = Execution outcome
```

Основной цикл:

```text
                 EVENT
                   │
                   ▼
                  FSM
                   │
                   ▼
                ACTION
                   │
                   ▼
                 TOOLS
                   │
                   ▼
            EXTERNAL WORLD
                   │
                   ▼
                 EVENT
```

Для Skill:

```text
Current State
      +
     Event
      +
     Guard
      ↓
   Actions
      ↓
  Next State
```

**Event является универсальным связующим механизмом между внешним миром, Tools, Runtime и FSM. При этом Event сообщает только о том, что произошло; решение о дальнейших действиях принадлежит Skill/FSM.**
