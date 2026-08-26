# Tool SDK Specification
## AI Agent Constructor — Draft v0.1

> Статус: архитектурный draft. Назначение: определить контракт между Tool и Agent Constructor / Runtime.

---

## 1. Что такое Tool

**Tool = capability агента.**

Tool предоставляет платформе техническую возможность взаимодействовать с внешним миром или инфраструктурой.

Примеры:

- Telegram
- CRM
- LLM
- Memory
- Web Search
- Files
- Saby
- Email

Основная модель:

```text
Agent
  └── Skill
       └── FSM
            └── Action
                 └── Tool
                      ├── Commands
                      ├── Events
                      └── State (optional)
```

Ключевая граница:

```text
Tool   = capability / возможность
Action = намерение / операция
Skill  = процесс, описанный FSM
```

Пример:

```text
Tool:
    telegram.send_message

Action:
    clarify_with_foreman

Skill:
    process_foreman_request
```

---

# 2. Главные принципы

### 2.1 Tool не содержит бизнес-логику агента

Tool не должен знать:

- что такое закупка;
- что такое заявка;
- кто такой прораб;
- как принимать бизнес-решение;
- какой Skill сейчас выполняется.

Плохо:

```text
telegram.send_clarification_for_request(...)
```

Хорошо:

```text
telegram.send_message(...)
```

Бизнес-смысл формируется Action и Skill.

### 2.2 Tool не управляет FSM

Tool может:

- выполнить Command;
- породить Event;
- сообщить собственное состояние.

Tool не должен самостоятельно менять State Skill.

```text
Tool
  ↓
Event
  ↓
Runtime
  ↓
FSM
```

### 2.3 Runtime не зависит от реализации Tool

Runtime работает с контрактом:

```text
Manifest
Commands
Events
Schemas
Lifecycle
```

а не с конкретной библиотекой или API.

### 2.4 Внешний мир подключается через Tools

Если агент взаимодействует с Telegram, CRM, LLM, Web, Files, Saby и т.д., это представляется Tool или Tool Adapter.

---

# 3. Состав Tool

Минимальная модель:

```text
Tool
├── Manifest
├── Commands
├── Events (optional)
├── State Model (optional)
├── Configuration
├── Credentials
└── Runtime implementation
```

---

# 4. Tool Manifest

Manifest — декларативное описание Tool, которое используется Builder и Runtime.

Пример:

```yaml
id: telegram
version: "1.0.0"

name: Telegram
description: "Communication through Telegram"

runtime:
  type: python

commands:
  - id: send_message
    input_schema: SendMessageInput
    output_schema: SendMessageResult

  - id: get_thread
    input_schema: GetThreadInput
    output_schema: GetThreadResult

events:
  - id: message.received
    payload_schema: MessageReceivedEvent

state:
  enabled: true
  states:
    - disconnected
    - connecting
    - connected

config:
  - id: api_id
    type: secret
    required: true

  - id: api_hash
    type: secret
    required: true
```

---

# 5. Tool ID

Tool ID должен быть:

- уникальным;
- стабильным;
- пригодным для DSL;
- независимым от реализации.

Примеры:

```text
telegram
crm
llm
memory
web
files
saby
```

---

# 6. Versioning

Tool использует SemVer:

```text
MAJOR.MINOR.PATCH
```

Например:

```text
telegram@1.2.0
```

Несовместимое изменение Command input/output требует MAJOR version.

Skill должен ссылаться на совместимую версию Tool.

---

# 7. Commands

Command — операция, которую Runtime может вызвать у Tool.

Пример:

```text
telegram.send_message
```

Command имеет:

```text
id
description
input schema
output schema
errors
execution mode
permissions
```

Пример:

```yaml
- id: send_message
  description: "Send a message"

  input_schema:
    type: object
    required:
      - chat_id
      - text

    properties:
      chat_id:
        type: string

      text:
        type: string

  output_schema:
    type: object
    properties:
      message_id:
        type: string
      sent_at:
        type: string
```

---

# 8. Command execution

Runtime вызывает Command через единый интерфейс:

```python
result = await tool.execute(
    command="send_message",
    input={
        "chat_id": "...",
        "text": "..."
    }
)
```

Tool возвращает структурированный CommandResult.

Runtime не должен знать внутренний API конкретного Tool.

---

# 9. Input / Output Schemas

Все Commands должны иметь явные schemas.

Рекомендуемый стандарт:

```text
JSON Schema
```

Это позволяет Builder:

- валидировать данные;
- строить UI;
- проверять Action;
- проверять совместимость;
- генерировать документацию.

---

# 10. Events

Event — факт, произошедший во внешнем мире или внутри Tool.

Например:

```text
telegram.message.received
```

Event содержит:

```text
id
type
timestamp
source
payload
metadata
correlation
```

Пример:

```json
{
  "id": "evt_123",
  "type": "telegram.message.received",
  "source": "telegram",
  "timestamp": "2026-08-26T18:00:00Z",
  "payload": {
    "chat_id": "123",
    "message_id": "456",
    "text": "Нужны грибки 10x100"
  },
  "correlation": {
    "conversation_id": "conv_123"
  }
}
```

---

# 11. Event не вызывает FSM напрямую

Tool публикует Event.

Runtime решает, какие Skill Runs заинтересованы событием:

```text
External World
      ↓
Tool
      ↓
Event
      ↓
Event Bus
      ↓
Event Router
      ↓
Skill Run
      ↓
FSM
```

Tool не знает, кто будет реагировать на Event.

---

# 12. Event correlation

Для долгоживущих процессов Event должен иметь возможность быть связанным с конкретным execution context.

Например:

```json
{
  "type": "telegram.message.received",
  "correlation": {
    "conversation_id": "conv_123",
    "external_thread_id": "telegram:chat:456"
  }
}
```

В дальнейшем correlation может включать:

```text
agent_run_id
skill_run_id
action_run_id
entity_id
conversation_id
external_id
```

---

# 13. Tool State

State — **optional capability**.

Не каждый Tool должен иметь собственную модель состояния.

Например Telegram:

```text
disconnected
connecting
connected
error
```

Но Memory Tool может вообще не иметь State.

---

# 14. Tool State и Skill State — разные вещи

Skill State:

```text
waiting_for_foreman
parsing
on_review
completed
```

Tool State:

```text
connected
disconnected
```

Они принадлежат разным уровням архитектуры.

---

# 15. Configuration

Tool может объявлять конфигурационные параметры:

```yaml
config:
  - id: base_url
    type: string
    required: true

  - id: timeout
    type: integer
    default: 30
```

Builder должен уметь отображать и валидировать эти параметры.

---

# 16. Credentials

Секреты не должны находиться внутри Skill или Action.

Концептуальная модель:

```text
Tool
  ↓
Connection
  ↓
Credential
```

Например:

```yaml
connection:
  tool: telegram
  credential: telegram_production
```

Credentials должны храниться в защищённом Secret Store.

---

# 17. Permissions

Command может объявлять необходимые permissions:

```yaml
permissions:
  - telegram.messages.send
```

Runtime проверяет право до выполнения:

```text
Agent
  ↓
Skill
  ↓
Action
  ↓
Tool Command
  ↓
Permission check
  ↓
Execution
```

---

# 18. Execution modes

Command может быть:

### Synchronous

```text
call
 ↓
result
```

### Asynchronous

```text
call
 ↓
execution_id
 ↓
later result / event
```

Это важно для операций, которые могут длиться долго.

---

# 19. Long-running operations

Tool не должен удерживать HTTP request или worker часами.

Вместо этого:

```text
Command
 ↓
execution_id
 ↓
waiting/running
 ↓
Event
 ↓
Runtime resumes Skill
```

Например:

```text
supplier.request_quote
```

может вернуть:

```json
{
  "execution_id": "exec_123",
  "status": "waiting"
}
```

Позже:

```text
supplier.quote.received
```

возобновляет Skill.

---

# 20. Errors

Ошибки должны быть структурированными:

```text
code
message
retryable
details
```

Например:

```json
{
  "code": "RATE_LIMITED",
  "message": "Rate limit exceeded",
  "retryable": true,
  "details": {
    "retry_after": 30
  }
}
```

Runtime должен различать:

```text
retryable
non_retryable
authentication_error
validation_error
permission_error
external_error
timeout
```

---

# 21. Idempotency

Commands, которые могут быть повторно вызваны после timeout или retry, должны поддерживать idempotency.

Например:

```text
telegram.send_message
```

может принимать:

```text
idempotency_key
```

чтобы повтор execution не создал дубликат.

---

# 22. Retries

Tool сообщает Runtime, является ли ошибка retryable.

Runtime управляет retry policy:

```text
retry immediately
exponential backoff
max attempts
dead letter
```

Глобальная retry policy не должна находиться внутри Tool.

---

# 23. Observability

Каждый Command execution должен иметь execution record:

```text
ToolExecution
├── execution_id
├── tool_id
├── command
├── status
├── duration
├── error
└── correlation_id
```

Payloads могут быть redacted.

Секреты никогда не должны попадать в обычные логи.

---

# 24. Tool Lifecycle

Предварительный lifecycle:

```text
REGISTERED
    ↓
VALIDATING
    ↓
INSTALLED
    ↓
ENABLED
    ↓
READY
    ↓
DISABLED
```

Runtime должен иметь возможность проверить health Tool.

---

# 25. Tool Health

Tool может предоставлять:

```python
await tool.health()
```

Пример:

```json
{
  "status": "healthy",
  "checks": {
    "api": "ok",
    "credentials": "ok"
  }
}
```

Builder может показывать:

```text
Telegram
● Connected
```

---

# 26. Tool Package

Концептуальная структура:

```text
telegram-tool/
├── manifest.yaml
├── schemas/
│   ├── send_message.json
│   └── message_received.json
├── src/
│   └── tool.py
└── README.md
```

Формат распространения пока не фиксируется.

Возможные варианты:

```text
Python package
Docker image
.tgz
Remote Tool
MCP adapter
```

---

# 27. Python SDK — предварительный интерфейс

Минимальный интерфейс:

```python
class Tool:

    @classmethod
    def manifest(cls) -> ToolManifest:
        ...

    async def initialize(self, config, credentials):
        ...

    async def execute(
        self,
        command: str,
        input: dict,
        context: ExecutionContext,
    ) -> CommandResult:
        ...

    async def health(self) -> HealthStatus:
        ...

    async def shutdown(self):
        ...
```

Events публикуются через Runtime context:

```python
await context.events.publish(event)
```

Tool не должен напрямую управлять Skill Runtime.

---

# 28. Execution Context

Tool получает ограниченный execution context:

```python
class ExecutionContext:

    execution_id: str
    agent_id: str
    skill_run_id: str
    action_run_id: str

    logger
    events
    secrets
```

Tool не получает весь внутренний объект Runtime.

Это ограничивает связанность и повышает безопасность.

---

# 29. Пример Telegram Tool

```yaml
id: telegram
version: "1.0.0"

commands:

  - id: send_message
    input_schema: SendMessageInput
    output_schema: SendMessageResult

  - id: get_thread
    input_schema: GetThreadInput
    output_schema: GetThreadResult

events:

  - id: message.received
    payload_schema: MessageReceivedEvent

state:
  enabled: true
  states:
    - disconnected
    - connecting
    - connected
```

---

# 30. Пример LLM Tool

```yaml
id: llm
version: "1.0.0"

commands:

  - id: run
    input_schema: LLMRequest
    output_schema: LLMResponse

  - id: run_structured
    input_schema: StructuredLLMRequest
    output_schema: StructuredLLMResponse
```

Provider скрыт за Adapter:

```text
LLM Tool
   ↓
Provider Adapter
   ├── OpenAI
   ├── Anthropic
   ├── Ollama
   └── other
```

Action работает с:

```text
llm.run_structured
```

а не с конкретным provider.

---

# 31. Пример CRM Tool

```yaml
id: crm
version: "1.0.0"

commands:

  - id: request.get
  - id: request.create
  - id: request.update
  - id: request.transition

events:

  - id: request.created
  - id: request.updated
  - id: request.status_changed
```

CRM Tool предоставляет интерфейс доступа к CRM.

Бизнес-решение:

```text
если request parsed → ready
```

остаётся в Skill FSM.

---

# 32. Tool и MCP

MCP можно рассматривать как один из способов реализации Tool.

Модель:

```text
Tool
├── Native Tool
├── MCP Tool
├── HTTP Tool
├── Python Tool
└── Remote Tool
```

Runtime видит одинаковый интерфейс:

```text
Tool
  → Command
  → Result
  → Event
```

MCP не является обязательной частью core-модели.

---

# 33. Что Tool НЕ должен делать

Tool не должен:

- запускать Skill;
- выбирать Action;
- принимать бизнес-решения;
- менять Skill State;
- выбирать следующий шаг;
- хранить бизнес-логику агента;
- обходить Permission System;
- управлять глобальной retry policy;
- напрямую управлять execution lifecycle Skill.

---

# 34. Что Tool ДОЛЖЕН делать

Tool должен:

- предоставлять capabilities;
- валидировать входные данные;
- выполнять Commands;
- возвращать структурированный результат;
- публиковать Events;
- сообщать ошибки;
- соблюдать permissions;
- поддерживать lifecycle;
- предоставлять health information;
- быть версионируемым.

---

# 35. Главная runtime-модель

```text
                AGENT
                  │
                SKILL
                  │
                 FSM
                  │
               ACTION
                  │
          ┌───────┴───────┐
          │               │
        TOOL            TOOL
          │               │
       command          command
          │               │
      external         external
       world             world
          │               │
          └────── EVENT ──┘
                  │
              EVENT BUS
                  │
                 FSM
```

Замкнутый цикл:

```text
Event
  ↓
FSM
  ↓
Action
  ↓
Tool
  ↓
External World
  ↓
Event
  ↓
FSM
```

---

# 36. Acceptance Criteria для SDK v0.1

SDK можно считать достаточно зрелым, если независимо можно реализовать:

```text
1. Telegram Tool
2. LLM Tool
3. CRM Tool
4. Memory Tool
```

и все они подключаются к Runtime через одну модель:

```text
Manifest
Commands
Schemas
Events
Execution
Errors
Health
```

При этом Runtime не содержит:

```text
if telegram ...
if openai ...
if crm ...
```

То есть:

> Runtime работает с Tool Protocol, а не с конкретными Tools.

---

# 37. Открытые вопросы

В v0.1 пока не фиксируются:

1. Точный формат Tool Package.
2. Python-only SDK или polyglot SDK.
3. Нужен ли отдельный Tool Server.
4. Нужна ли sandboxing-модель.
5. Multi-tenant isolation.
6. Remote Tool marketplace.
7. Streaming API.
8. Transactions.
9. Нужно ли делать MCP first-class protocol.
10. Насколько формальным должен быть Tool State.
11. Нужна ли отдельная Connection abstraction.
12. Может ли Tool иметь собственные background workers.
13. Как Tool получает секреты в разных deployment modes.
14. Как ограничивать ресурсы Tool.
15. Как Tool публикуется и устанавливается через Builder.

---

# 38. Следующие документы

После Tool SDK логично формализовать:

```text
docs/
├── TOOL_SDK_SPEC.md
├── ACTION_SPEC.md
├── SKILL_SPEC.md
├── EVENT_SPEC.md
└── RUNTIME_SPEC.md
```

Порядок:

```text
TOOL
  ↓
ACTION
  ↓
SKILL / FSM
  ↓
EVENT MODEL
  ↓
RUNTIME
```

Это позволит постепенно превратить архитектурную концепцию в реализуемую платформу.
