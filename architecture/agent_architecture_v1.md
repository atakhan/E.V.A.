# Архитектура конструктора ИИ-агентов
## Рабочая версия архитектурной концепции

> **Статус:** conceptual / non-normative — мотивация и модель, не контракт реализации.  
> **Нормативные спеки:** [`docs/ACTIONS_SPEC_v0.1.md`](../docs/ACTIONS_SPEC_v0.1.md), [`SKILLS_SPEC_v0.1.md`](../docs/SKILLS_SPEC_v0.1.md), [`EVENT_SPEC_v0.1.md`](../docs/EVENT_SPEC_v0.1.md), [`TOOLS_SDK_SPEC_v0.1.md`](../docs/TOOLS_SDK_SPEC_v0.1.md), [`RUNTIME_SPEC_v0.1.md`](../docs/RUNTIME_SPEC_v0.1.md)  
> **Взаимодействие (target):** [`docs/INTERACTION_SPEC_v0.1.md`](../docs/INTERACTION_SPEC_v0.1.md)  
> **Согласование:** [`docs/ARCHITECTURE_DOCS_ALIGNMENT.md`](../docs/ARCHITECTURE_DOCS_ALIGNMENT.md)

Документ фиксирует текущие выводы и наработки по архитектуре конструктора ИИ-агентов, возникшие при проектировании ИИ-агента для снабжения. При расхождении с `docs/*_SPEC` приоритет у спеков. Слой человек ↔ агент (стол, голос, диспетчер): [`INTERACTION_SPEC`](../docs/INTERACTION_SPEC_v0.1.md) — target; исполнение уже выбранной работы — RUNTIME/SKILLS.

---

# 1. Исходная идея

Первоначально проектировался конкретный ИИ-агент для снабжения.

В процессе проработки стало очевидно, что значительная часть его архитектуры не относится непосредственно к снабжению. Возникает возможность сделать более универсальную систему:

**Конструктор ИИ-агентов**, в котором поведение агента проектируется визуально на холсте.

Конкретный ИИ снабженца в таком случае является одним из агентов, собранных на общем фундаменте конструктора.

Главная идея:

> Человек проектирует поведение агента, а runtime исполняет это поведение.

---

# 2. Центральная модель

На текущем этапе формируется связка:

**Tools → Actions → Skills → Agent**

При этом Skill описывается через FSM:

**Skill → FSM → States + Events → Actions**

Получается:

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
                        ACTIONS
                           │
                      Action Recipe
                           │
                           ▼
                         TOOLS
```

Ключевые определения:

### Tool

**Что агент умеет делать.**

Tool предоставляет агенту конкретную capability и интерфейс взаимодействия с внешним миром или внутренними системами.

Примеры:

- LLM
- Memory
- Telegram
- CRM
- Catalog
- Web Search
- Files
- Saby

### Action

**Что агент хочет сделать.**

Action — именованная операция агента, которая собирается из Tools по определённому рецепту.

Примеры:

- `ingest_channel_message`
- `parse_request`
- `clarify_with_foreman`
- `propose_normalization`
- `learn_from_correction`
- `show_tmc_alternatives`
- `accept_manual_input`
- `batch_parse_requests`
- `batch_confirm_requests`

Action — важная промежуточная абстракция между FSM и Tools.

### Skill

**Как агент решает определённый класс задач.**

Skill — более высокоуровневый процесс, имеющий собственную FSM.

Пример:

`process_foreman_request`

может иметь состояния:

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
↓
COMPLETED
```

### Agent

**Кто этот агент и каким поведением/способностями он обладает.**

Например:

```text
Procurement Agent

Skills:
- process_foreman_request
- find_suppliers
- negotiate_price
- request_invoice
- process_invoice
- track_shipment
- daily_reflection

Tools:
- LLM
- Memory
- Telegram
- CRM
- Catalog
- Saby
- Web Search
```

---

# 3. FSM как язык описания Skill

FSM не рассматривается как самостоятельная бизнес-сущность верхнего уровня.

Лучше считать:

> Skill — это процесс, а FSM — способ описать управление этим процессом.

Поэтому структура:

```text
Skill
└── FSM
    ├── States
    └── Events
```

В FSM состояние описывает, **где сейчас находится процесс**, а событие — **что произошло**.

Пример:

```yaml
id: skill.example
version: "0.3.0"
description: "..."
initial: state_name

states:
  state_name:
    on_enter:
      - action_id

    on:
      event.type:
        - guard: "expr"
          actions:
            - action_id
          to: other_state

    final: true

params:
  - name: request_id
    required: true
```

---

# 4. Transition

Отдельную сущность `Transition` пока не вводим.

Логически переход существует:

```text
State + Event + Guard + Actions + Next State
```

Но он может быть представлен непосредственно внутри FSM:

```yaml
waiting_for_foreman:

  on:

    channel.message.received:
      - guard: "event.conversation_id == task.conversation_id"
        actions:
          - parse_response
        to: analyzing
```

Таким образом:

```text
State
└── Event handler
    ├── Guard
    ├── Actions
    └── Next State
```

Это уменьшает количество сущностей и делает модель конструктора проще.

---

# 5. Tool Interface

Изначальная идея: каждый Tool должен соответствовать интерфейсу конструктора.

Предварительная структура:

```text
Tool
├── Commands
├── Events
└── States (optional)
```

## Commands

Команды, которые могут вызываться агентом.

Примеры:

```text
telegram.send_message
crm.update
memory.search
llm.run
```

## Events

События, которые Tool способен генерировать.

Например Telegram Tool:

```text
channel.message.received
```

CRM Tool:

```text
crm.request.created
crm.request.updated
```

## States

Состояния Tool могут существовать, если конкретный Tool действительно обладает собственным жизненным циклом.

Например:

```text
connected
disconnected
```

Но важный вывод:

> Tool не обязан иметь собственную FSM или States.

Для некоторых Tools состояние может быть бессмысленным.

Поэтому состояние Tool — опциональная часть интерфейса.

## Tool Type и Tool Instance

В платформе Tool существует на двух уровнях (см. [`TOOLS_SDK_SPEC` §39](../docs/TOOLS_SDK_SPEC_v0.1.md#39-instance-based-tools-v02)):

| Уровень | Что это | Пример |
|---------|---------|--------|
| **Tool Type** | Запись в глобальной библиотеке: commands, events, `configSchema` | `telegram`, `polza_ai_llm` |
| **Tool Instance** | Экземпляр у конкретного агента: credentials, config, enabled | `foreman_telegram` |

Action Recipe ссылается на **instance id**, не на type id напрямую. Type определяет контракт plugin; Instance — конкретное подключение агента к внешнему миру.

---

# 6. Action как рецепт

Action не должен напрямую становиться FSM.

Action — исполняемая операция.

> Иллюстрация ниже — shorthand. Нормативный формат recipe: [`ACTIONS_SPEC_v0.1`](../docs/ACTIONS_SPEC_v0.1.md) (`steps[]` с `tool`, `input`, `when`).

Пример:

```yaml
id: parse_request

input:
  message: event.payload

recipe:

  - context.build:
      recipe: foreman_request_v1

  - memory.search:
      ...

  - catalog.search_tmc:
      ...

  - llm.run_structured:
      schema: ParsedRequestV1

  - crm.update:
      ...
```

Таким образом:

```text
FSM
 ↓
Action
 ↓
Action Recipe
 ↓
Tools
```

FSM не знает, какие именно Tools используются внутри Action.

Это важная степень абстракции.

---

# 7. Runtime

Runtime должен превратить декларативную модель конструктора в работающего агента.

Предварительная схема:

```text
EVENT
  ↓
ROUTING
  ↓
SKILL RUN
  ↓
FSM
  ↓
ACTION
  ↓
ACTION RECIPE
  ↓
TOOLS
  ↓
RESULT / DOMAIN EVENT
  ↓
FSM
```

Более подробно:

```text
External World
      │
      ▼
    Tool
      │
      ▼
    Event
      │
      ▼
 Event Routing
      │
      ▼
 Skill Run
      │
      ▼
 FSM evaluation
      │
      ▼
 Action
      │
      ▼
 Action Recipe
      │
      ▼
 Tools
      │
      ▼
 External World
```

---

# 8. Event-driven модель

Главный принцип runtime:

> Runtime реагирует на события, а не постоянно опрашивает состояние.

Например:

```text
Telegram
↓
channel.message.received
↓
найдены подходящие Skill Runs
↓
FSM получает Event
↓
производится переход
↓
выполняются Actions
```

Tool не должен напрямую знать о Skills.

Telegram Tool не должен делать:

```text
FSM.handle(...)
```

Вместо этого:

```text
Telegram Tool
↓
Event
↓
Event infrastructure
↓
подходящие Skill Runs
```

Это развязывает Tools и Skills.

---

# 9. Skill Definition и Skill Run

Важно различать описание Skill и конкретный запущенный экземпляр.

```text
Skill Definition
    process_foreman_request
```

и:

```text
Skill Run #8291
    skill_id: process_foreman_request
    current_state: WAITING_FOR_FOREMAN
    params:
      request_id: 123
```

Один Skill может иметь много одновременно работающих экземпляров.

Поэтому runtime должен хранить состояние конкретного Skill Run.

Skill Run содержит как минимум:

```text
skill_id
current_state
params
local variables
execution status
correlation information
```

---

# 10. Долгоживущие процессы

Action не должен висеть часами или днями.

Например:

```text
Action: request_supplier_quote
```

отправляет сообщение поставщику и завершается.

Skill после этого переходит:

```text
WAITING_FOR_SUPPLIER
```

и приостанавливается.

Через несколько часов приходит:

```text
supplier.reply.received
```

После чего Skill Run возобновляется.

Таким образом:

> Долгоживущий процесс принадлежит Skill Run, а не Action.

Это позволяет строить процессы продолжительностью от секунд до нескольких дней.

---

# 11. Guards

Один Event может иметь несколько вариантов поведения.

Например:

```yaml
message.received:

  - guard: "confidence > 0.9"
    to: ready

  - guard: "confidence <= 0.9"
    actions:
      - clarify
    to: clarifying
```

Получается:

```text
                 Event
                   │
             ┌─────┴─────┐
             ▼           ▼
          Guard A      Guard B
             │           │
          Actions      Actions
             │           │
             ▼           ▼
          State A      State B
```

Guard является частью описания поведения FSM, а не отдельной архитектурной сущностью.

---

# 12. Domain Events и Runtime Events

Важно разделить два типа событий.

## Domain Events

События, значимые для поведения агента:

```text
channel.message.received
supplier.reply.received
human.request.approved
human.request.rejected
invoice.received
request.confirmed
```

Они могут влиять на FSM. Канон human-in-the-loop: [`EVENT_SPEC` §34](../docs/EVENT_SPEC_v0.1.md#34-human-events).

## Runtime / System Events

Технические события:

```text
tool.execution.started
tool.execution.completed
action.execution.failed
skill.run.started
skill.run.completed
action.<action_id>.completed
```

`action.<action_id>.completed` — синтезируется Runtime после Action и может использоваться FSM. Generic `action.completed` — только observability (см. [`EVENT_SPEC` §32](../docs/EVENT_SPEC_v0.1.md#32-system-events)).

Они нужны для:

- логирования;
- observability;
- debugging;
- metrics.

Но обычно не должны использоваться FSM как бизнес-события.

---

# 13. Action Result

Action может завершиться результатом.

Например:

```text
parse_request
→
{
  items: [...],
  confidence: 0.91,
  missing_fields: []
}
```

Результат может стать основанием для дальнейшего поведения FSM.

При этом технические события выполнения Action могут автоматически генерироваться runtime.

Не нужно заставлять каждый Action вручную делать:

```text
log.append
```

---

# 14. Логирование

Logging — инфраструктурная возможность runtime, а не обязательная часть каждого Action.

Runtime автоматически может фиксировать:

```text
Event
Action started
Tool called
Tool result
Action completed
State changed
Skill completed
Error
```

Поэтому `log.append` не обязательно включать в каждый Action Recipe.

Это cross-cutting concern.

---

# 15. Event Routing

Event Router необходим технически, но не является отдельной концептуальной сущностью конструктора.

Пользователь видит:

```text
Event
```

а runtime решает:

```text
какие активные Skill Runs заинтересованы этим Event?
```

Например:

```text
channel.message.received
        ↓
Skill Run #101 → подходит
Skill Run #102 → подходит
Skill Run #103 → не подходит
```

Для этого Event должен содержать correlation information.

Например:

```json
{
  "type": "channel.message.received",
  "correlation": {
    "channel": "telegram",
    "conversation_id": "123"
  },
  "payload": {}
}
```

---

# 16. Что не стоит делать отдельными сущностями конструктора

В ходе ревизии первоначальной архитектуры некоторые модули были признаны скорее инфраструктурой:

```text
FSM Engine
Event Router
Event Bus
Action Executor
Tool Executor
LLM Engine
Logs Manager
```

Они нужны runtime, но не должны перегружать концептуальную модель конструктора.

Также пока не стоит без необходимости создавать:

```text
Session Manager
Task Manager
Context Manager
```

Возможно, их функции будут естественно покрываться уже существующими сущностями.

---

# 17. Session

Отдельная глобальная Session пока не нужна.

Есть:

```text
Agent
Skill
Skill Run
Conversation
Business Entity
```

Каждая из этих сущностей имеет собственную ответственность.

Не стоит заранее создавать:

```text
Session
├── Context
├── Tasks
├── Memory
├── State
└── ...
```

потому что это легко превращается в универсальный контейнер, знающий обо всём.

Потребность в отдельной Session можно вернуть, если она реально возникнет из требований runtime.

---

# 18. Context

Context не обязательно должен быть фундаментальной сущностью архитектуры.

Операция:

```text
context.build
```

может быть Tool Command.

Например Action:

```text
parse_request
```

использует:

```text
context.build
memory.search
catalog.search_tmc
llm.run_structured
crm.update
```

При этом внутри runtime может существовать Context Engine, который знает, как собирать контекст.

То есть:

```text
Context Engine
```

— инфраструктура,

а:

```text
context.build
```

— capability.

---

# 19. Memory

Memory естественно вписывается в модель как Tool.

Например:

```text
Memory Tool
├── search
├── propose
├── store
└── ...
```

Память может содержать выводы и знания:

```text
"грибок" → дюбель с термоголовкой 10×100
```

а также информацию о:

- пользователях;
- поставщиках;
- ТМЦ;
- предпочтениях;
- способах обработки;
- прошлых решениях.

Конкретная реализация памяти может включать Entity Graph, vector search, structured data и другие механизмы.

Но они не обязаны становиться отдельными сущностями конструктора.

---

# 20. Entity Graph

Entity Graph можно рассматривать как реализацию Tool или Memory capability.

Например:

```text
Entity Graph Tool
```

или часть:

```text
Memory Tool
```

Главное — не заставлять Skill знать о конкретной технологии хранения.

Skill должен мыслить на уровне:

```text
memory.search
```

а не:

```text
neo4j.query
```

если это не является осознанной частью дизайна конкретного Tool.

---

# 21. Business Data

Вместо большого:

```text
Business Data Module
```

можно иметь специализированные Tools:

```text
CRM Tool
Catalog Tool
BPM Tool
Saby Tool
1C Tool
```

Это хорошо соответствует общей модели конструктора.

---

# 22. Reflection

Reflection не обязательно должен быть уникальным системным модулем.

Он может быть обычным Skill:

```text
Skill: daily_reflection

START
 ↓
collect_execution_history
 ↓
analyze_failures
 ↓
identify_patterns
 ↓
generate_memory_candidates
 ↓
validate_candidates
 ↓
save_memory
 ↓
COMPLETED
```

Tools:

```text
Logs
Memory
LLM
```

Это важный тест универсальности платформы:

> Если рефлексия агента может быть построена тем же конструктором, значит конструктор действительно описывает поведение, а не только бизнес-логику снабжения.

---

# 23. Planner

Planner пока оставлен открытым вопросом.

Он отличается от Skill тем, что отвечает не столько на:

> Как выполнить процесс?

сколько на:

> Какие процессы вообще нужно запустить?

Возможные варианты:

```text
Planner
↓
создаёт Skill Runs
```

или:

```text
Planner как специальный системный runtime-механизм
```

или в будущем:

```text
Planner Skill
```

На текущем этапе не нужно преждевременно фиксировать решение.

---

# 24. Концептуальное ядро конструктора

После ревизии архитектура сильно упрощается.

Основные сущности:

```text
Agent
Skill
Action
Tool
```

FSM является моделью поведения Skill:

```text
Skill
└── FSM
    ├── State
    └── Event
```

Action использует Tools:

```text
Action
└── Recipe
    └── Tools
```

И получается:

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
                        ACTIONS
                           │
                      ACTION RECIPE
                           │
                           ▼
                         TOOLS
```

---

# 25. Главные определения модели

Можно свести всё к пяти вопросам:

| Сущность | Вопрос |
|---|---|
| **Tool** | Что агент умеет делать? |
| **Action** | Что агент делает? |
| **Skill** | Как агент решает определённый класс задач? |
| **State** | Где сейчас находится процесс? |
| **Event** | Что произошло? |

А:

| Механизм | Роль |
|---|---|
| **FSM** | Управляет поведением Skill |
| **Runtime** | Исполняет декларацию агента |
| **Event routing** | Доставляет события нужным Skill Runs |
| **Logging** | Автоматически фиксирует выполнение |
| **Persistence** | Хранит состояние |
| **LLM runtime** | Исполняет LLM Tools |

---

# 26. Пример: ИИ снабженца

Конкретный агент:

```text
Procurement Agent
```

Tools:

```text
LLM
Memory
Telegram
CRM
Catalog
Saby
Web Search
Files
```

Skills:

```text
process_foreman_request
find_suppliers
negotiate_supplier
request_invoice
process_invoice
track_shipment
daily_reflection
```

Например:

```text
Skill: process_foreman_request

NEW
 ↓
ANALYZING
 ↓
 ┌───────────────┐
 │               │
 ▼               ▼
READY        CLARIFYING
                 ↓
          WAITING_FOR_FOREMAN
                 ↓
             ANALYZING
                 ↓
               READY
```

Actions:

```text
ingest_channel_message
parse_request
clarify_with_foreman
propose_normalization
learn_from_correction
show_tmc_alternatives
accept_manual_input
batch_parse_requests
batch_confirm_requests
```

Tools внутри этих Actions:

```text
Telegram
CRM
Memory
Catalog
LLM
Context
UI
```

---

# 27. Runtime-пример

Прораб пишет:

> «Нужны грибки 10×100, 200 штук»

### Tool

Telegram Tool получает сообщение.

Создаётся:

```text
channel.message.received
```

### Runtime

Находит подходящий Skill Run.

### FSM

Skill находится:

```text
WAITING_FOR_MESSAGE
```

Событие приводит к:

```text
Action: ingest_channel_message
State: ANALYZING
```

### Action

Выполняет:

```text
context.build
memory.search
catalog.search
llm.run_structured
crm.update
```

### Результат

LLM определяет:

```text
"грибки"
→ тарельчатый дюбель
```

с определённой уверенностью.

### FSM

Если уверенность недостаточная:

```text
CLARIFYING
```

Action:

```text
clarify_with_foreman
```

После отправки сообщения:

```text
WAITING_FOR_FOREMAN
```

Skill Run приостанавливается.

Через несколько часов приходит:

```text
channel.message.received
```

Runtime снова доставляет событие тому же Skill Run.

FSM продолжает выполнение.

---

# 28. Главная архитектурная идея

Вся система постепенно сводится к очень компактной модели:

```text
Tool = capability
Action = operation
Skill = process
FSM = process control
State = current position in process
Event = fact that happened
Agent = composition of behavior and capabilities
```

А runtime:

```text
Event
 ↓
Skill Run
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

# 29. Что зафиксировано и что остаётся открытым

Большинство вопросов из предыдущей версии §29 решены в нормативных спеках. Полный decision log: [`ARCHITECTURE_DOCS_ALIGNMENT.md`](../docs/ARCHITECTURE_DOCS_ALIGNMENT.md).

## Решено в спеках

| Тема | Где |
|------|-----|
| Event routing, multi-skill | EVENT §21, RUNTIME §15 |
| Action Recipe format | ACTIONS_SPEC |
| Human approval events | EVENT §34 (`human.request.*`) |
| Action completion in FSM | RUNTIME §14 (`action.<id>.completed`) |
| Tool Type / Instance | TOOLS_SDK §39 |
| Version pinning (контракт) | RUNTIME §4 |
| FSM Canvas | FSM_CANVAS_STYLE.md |

## Остаётся открытым

1. **Planner** — приоритизация и планирование Skill Runs (вне scope v0.1). Диспетчер очередного акта человека — отдельно: [`INTERACTION_SPEC`](../docs/INTERACTION_SPEC_v0.1.md).
2. **Multi-tenant** — изоляция агентов, credentials, quotas на уровне платформы.
3. **Advanced observability** — distributed tracing, execution replay, audit UI.

Эти темы лучше решать после стабилизации runtime v0.1.

---

# 30. Следующий архитектурный эксперимент

Не стоит пока добавлять новые модули.

Следующий шаг:

**взять реальный процесс ИИ снабженца и полностью выразить его через текущую модель.**

Например:

```text
process_foreman_request
```

и пройти его целиком:

```text
Events
 ↓
States
 ↓
Actions
 ↓
Tools
 ↓
Results
 ↓
Events
```

Затем таким же образом проверить:

```text
negotiate_supplier
```

и:

```text
process_invoice
```

Если три существенно разных процесса выражаются без специальных «снабженческих» сущностей и костылей, это будет сильным подтверждением того, что ядро конструктора действительно универсально.

---

# Итоговая рабочая формула

```text
                    AI AGENT BUILDER
                           │
                           ▼
                         AGENT
                           │
                         SKILLS
                           │
                           ▼
                          FSM
                     ┌─────┴─────┐
                     ▼           ▼
                   STATE        EVENT
                     │           │
                     └─────┬─────┘
                           ▼
                         ACTION
                           │
                           ▼
                       RECIPE
                           │
                           ▼
                         TOOLS
                           │
                           ▼
                    EXTERNAL WORLD
                           │
                           ▼
                         EVENT
                           │
                           └──────────► FSM
```

**Текущий главный вывод:** мы больше не проектируем «ИИ снабженца». Мы постепенно проектируем **язык и runtime для описания поведения ИИ-агентов**, а снабженец становится первым сложным примером такого агента.
