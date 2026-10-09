# Behavior Spec — v1

> Нормативный контракт семантической модели поведения агента (Behavior Graph).  
> **Статус: архив.** Снят как канон конструктора. Редактор снова пишет FSM (`states[]`): [`../SKILLS_CONSTRUCTOR.md`](../SKILLS_CONSTRUCTOR.md).  
> Видение эксперимента: [`NEW_CONSTRUCTOR_DESC.md`](./NEW_CONSTRUCTOR_DESC.md).  
> Не использовать при реализации холста или publish.

**Статус:** снят. UI конструктора — FSM-холст, не проекция этого контракта.

---

## 1. Принцип

```text
Source of truth — не Story и не FSM.
Source of truth — Behavior Graph (семантическая модель поведения).
Story — представление для человека.
FSM  — исполняемый артефакт (machine code).
```

```text
             HUMAN DOMAIN
                  │
                  ▼
        ┌──────────────────┐
        │  Behavior Graph  │ ← Source of Truth
        └────────┬─────────┘
                 │
          validate / compile   (publish)
                 │
                 ▼
        ┌──────────────────┐
        │ execution.states │ ← Artifact  compilerVersion
        └────────┬─────────┘
                 │
                 ▼
              Runtime
```

Runtime **не читает** Behavior Graph. Он читает скомпилированные `states[]` как сегодня.

В v1 **никто не редактирует FSM**. Story и Logic пишут только в граф. Двустороннее Behavior ↔ FSM запрещено.

Продукт: **конструктор поведения AI-агента**, не FSM-конструктор.

---

## 2. Слои

| Слой | Имя | Кто редактирует |
|------|-----|-----------------|
| Human | **Story** | Behavior Graph, человеческий язык |
| Human | **Logic / Behavior** | тот же граф, технический язык |
| Artifact | **Execution / FSM** | никто (read-only preview) |
| Live | **Runtime** | никто (подсветка узлов по origin) |

UI v1: вкладки **История · Логика · Runtime**. Execution — панель «Машина» / YAML `# GENERATED`.

---

## 3. Save vs publish

`states[]` — materialized execution artifact, **не** второй source of truth.

### 3.1 Draft save / autosave

Сохраняется канон:

- `behavior` (узлы, рёбра, titles, explanation, layout)
- `params`, метаданные skill (`id`, `name`, `description`, `version`)
- `storyViewport` / `logicViewport`

Допускается:

- незавершённый граф
- `compile` с ошибками (draft не блокируется)
- ephemeral `execution` preview в редакторе (не обязан совпадать с `states[]` черновика)

Draft **не обязан** содержать валидный FSM. Симуляция live-run идёт по **publication**.

### 3.2 Publish

```text
behavior → validate (errors) → compile → execution artifact → published agent
```

Если у skill нет `behavior` (legacy FSM-only): публикуются существующие `states[]` без компиляции.

Если `behavior` есть: `states[]` **перезаписываются** результатом compile. Старые id состояний (`IDLE`) могут смениться на детерминированные `s_*`. Это нормально: поведение проверяется equivalence, не именами.

Publish **отклоняется**, если compile/validate вернули errors.

Published skill:

```yaml
behavior: { ... }          # канон
execution:
  compilerVersion: "1"
  compiledAt: "<iso>"
  states: [...]            # GENERATED — DO NOT EDIT
# Плоский states[] дублирует execution.states, пока runtime mapper читает корень skill.
states: [...]
```

---

## 4. Behavior Graph

```json
{
  "version": 1,
  "entry": "node_wait_IDLE",
  "nodes": [],
  "edges": []
}
```

- `version` — схема графа (сейчас `1`), не путать с `compilerVersion`.
- `entry` — id узла входа. В v1: `wait`. Пустая строка / `null` = граф ещё не начат (draft).
- Узлы и рёбра имеют **стабильные id**. Compiler **никогда** не переиздаёт id узла Behavior.

Рекомендуемый формат id:

- UI: `node_<uuid>`, `edge_<uuid>`
- Lift из FSM: `node_wait_<stateId>`, `node_do_<transitionId>_<actionId>`, `node_decide_<stateId>_<eventSlug>`, `node_end_<stateId>`, `edge_<from>_<to>_<n>`

Id переживают compile, save, reload, смену layout.

### 4.1 Общие поля узла

```ts
type LayoutRect = { x: number; y: number; width?: number; height?: number }

type Explanation = {
  what?: string
  why?: string
  when?: string
  until?: string
  result?: string
}

type NodeBase = {
  id: string
  title: string
  explanation?: Explanation
  layout?: { story?: LayoutRect; logic?: LayoutRect }
}
```

Два layout обязательны как раздельные пространства. Story — почти линейный столбец. Logic — дерево с ветками.

### 4.2 `wait`

Ожидание. Не путать с `end`.

```ts
type WaitFor =
  | { type: "event"; event: string }
  | { type: "action"; actionId: string }
  | { type: "input"; event?: string }       // default: channel.message.received
  | { type: "condition"; event: string; expression: string }

type WaitNode = NodeBase & {
  type: "wait"
  waitFor: WaitFor
}
```

| `waitFor.type` | Смысл | Событие FSM |
|----------------|--------|-------------|
| `event` | Когда случается факт | `event` |
| `action` | Ждём завершения action, **не** запускаем его | `action.<actionId>.completed` |
| `input` | Ждём ответ человека | `event` или `channel.message.received` |
| `condition` | Ждём событие, пока выражение истинно | `event` + guard = `expression` |

«Жду следующего сообщения» в цикле диалога — это **`wait`**, не `end`.

Исходящие: не более одного смыслового продолжения (рёбра `next` / `loop`). Несколько веток — через `decide`.

### 4.3 `do`

Глагол. Ссылка на Action catalog агента.

```ts
type DoNode = NodeBase & {
  type: "do"
  actionId: string
}
```

- `title` по умолчанию = `ActionDef.name`; технический `actionId` показывается вторично.
- Добавить шаг на canvas = **создать узел + ребро**, никогда строка в `transition.actions`.
- Compiler ставит `actionId` на **входящий** переход к состоянию `s_<doId>` и ждёт `action.<actionId>.completed` **в этом** состоянии.

### 4.4 `decide`

Развилка. Сама **не** является FSM state.

```ts
type DecideBranch = {
  id: string
  label: string   // semantic: «Да» / «Нет» / «Несколько вариантов»
  guard: string   // machine: results.length > 1
  to: string      // node id
}

type DecideNode = NodeBase & {
  type: "decide"
  question: string
  branches: DecideBranch[]
}
```

- `question` / `label` — человеческий слой.
- `guard` — машинный слой (тот же expression engine, что SKILLS_SPEC).
- Порядок `branches` = порядок handler'ов FSM (детерминизм).
- Пустой `guard` на последней ветке = else.
- Цель ветки: `wait` | `do` | `end`. Цель `decide` в v1 запрещена (нет вложенных decide без промежуточного узла).
- Рёбра `edges[]` **не** дублируют ветки decide.

### 4.5 `end`

Только **завершение задачи** (`final: true`). Не «жду следующего события».

```ts
type EndNode = NodeBase & { type: "end" }
```

### 4.6 Рёбра

```ts
type BehaviorEdge = {
  id: string
  from: string
  to: string
  kind: "next" | "loop"
}
```

- `next` / `loop` компилируются одинаково (`to`). `loop` — подсказка Story («возвращаемся»).
- Источник: `wait` | `do` | `end` (у `end` исходящих быть не должно).
- `decide` связывается только через `branches[].to`.

### 4.7 Инварианты графа (validate)

Ошибки (блокируют publish, на draft — тоже видны в инспекторе):

- неизвестный `entry`
- висячий `to` / `from`
- `do` без `actionId`
- `wait.event` / `wait.condition` без event
- `decide` без веток или с `to` на другой `decide`
- больше одного исходящего `next|loop` у `wait`/`do`
- цикл без `wait` (busy loop) — warning
- неизвестный `actionId` относительно каталога агента — error на publish, warning на draft если каталог пуст

Пустой граф (`nodes=[]`) — warning, не error (draft). Publish skill без behavior и без states — как сегодня (`skill_empty`).

---

## 5. Compiler

`compilerVersion`: **`"1"`**.

Правила:

1. **Детерминизм.** `compile(B) === compile(B)` структурно: порядок `states` и `transitions`, id, guards, actions. Запрещены `uuid4` / `now` в id. `compiledAt` в метаданных artifact **не** входит в сравнение equivalence.
2. **Стабильные FSM id** производны от behavior node/edge id:
   - state: `s_<sanitize(nodeId)>`
   - transition: `t_<sanitize(edgeOrBranchId)>`
   - `sanitize`: `[^A-Za-z0-9_]+` → `_`
3. Behavior node id **не меняются**.
4. Каждый сгенерированный state несёт **`originNodeId`**. Каждый transition — **`originEdgeId`** (id ребра или ветки). Это обязательный контракт overlay.
5. `decide` не создаёт state.
6. Actions ставятся на transitions, `onEnter` compiled states пустой.
7. `end` → `final: true`.

### 5.1 Событие завершения узла

| Узел | Event, с которого уходим дальше |
|------|----------------------------------|
| `wait` event/input | `waitFor.event` (input: default `channel.message.received`) |
| `wait` action | `action.<actionId>.completed` |
| `wait` condition | `waitFor.event` + guard `expression` на исходящих |
| `do` | `action.<actionId>.completed` |

### 5.2 Лист цели

Переход **к** узлу T:

| T | `actions` | `to` |
|---|-----------|------|
| `do` | `[T.actionId]` | `s_<T.id>` |
| `wait` | `[]` | `s_<T.id>` |
| `end` | `[]` | `s_<T.id>` |
| `decide` | развернуть ветки на **том же** event источника | — |

Пример `wait(E) → do(A) → do(B) → wait(E)`:

```text
s_W  -- E / [A]                         --> s_A     originEdge: edge W→A
s_A  -- action.A.completed / [B]        --> s_B     originEdge: edge A→B
s_B  -- action.B.completed / []         --> s_W     originEdge: edge B→W
```

`do(A) → decide(q)`:

```text
s_A  -- action.A.completed [g1] / ... --> ...
s_A  -- action.A.completed [g2] / ... --> ...
```

Порядок веток = порядок `branches`.

### 5.3 Artifact

```ts
type ExecutionArtifact = {
  compilerVersion: "1"
  compiledAt?: string
  initial: string
  states: CompiledState[]
}

type CompiledState = {
  id: string
  name?: string
  originNodeId: string
  onEnter: []
  final: boolean
  transitions: CompiledTransition[]
  x: number
  y: number
  width: number
  height: number
}

type CompiledTransition = {
  id: string
  event: string
  guard: string
  actions: string[]
  to: string
  originNodeId: string
  originEdgeId: string
}
```

Layout compiled FSM: топологический порядок от `entry`, шаг `x += 220`. Нужен только для read-only «Машина».

Ошибки compile (невалидный граф) → `{ ok: false, errors: [...] }`, artifact не пишется.

---

## 6. Lift (FSM → Behavior)

Одноразово для skill **без** `behavior`.

Идея: FSM-state, который ждёт `action.X.completed`, **и** на вход в него пришли `actions` содержащие `X`, — это не `wait`, а **неявное завершение `do(X)`**.

- State с domain-event / `input` / чужим `action.completed` → `wait`
- Actions на transition → цепочка `do`
- Несколько handler'ов одного event или любой `guard` → `decide`
- `final` без исходящих → `end`
- Переход обратно в уже созданный wait → ребро `loop`

`razgovor` (IDLE → THINKING → REPLIED → IDLE) поднимается в:

```text
wait (channel.message.received)
  → do draft_reply
  → do send_reply
  → loop wait
```

Не `end`.

Если `behavior` уже есть — lift **не** запускается. Редактор не патчит `states`.

---

## 7. Behavioral equivalence

Сравнение двух FSM **не** byte-to-byte и **не** по именам states.

Два автомата эквивалентны, если их начальные состояния **бисимулярны** по метке перехода:

```text
(event, normalize(guard), tuple(actions))
```

`normalize(guard)`: trim + сжатие whitespace. Пустой guard = `""`.

Id states, layout, `origin*`, `compiledAt` игнорируются.

Тесты:

- `compile(B)` идемпотентен
- `lift(razgovor FSM) → compile` эквивалентен исходному razgovor
- ветвление с двумя guard сохраняет оба пути

---

## 8. Overlay runtime

```text
run.currentState  →  compiled state.originNodeId  →  Behavior node  →  подсветка карточки
history[]         →  посещённые originNodeId
actionRuns        →  do-узлы по actionId (доп. сигнал)
```

Не показывать пользователю `THINKING` / `s_node_…` как основной язык.

---

## 9. Нарратив («просмотреть как историю»)

Детерминированный обход от `entry`, **не LLM**.

| Узел | Шаблон |
|------|--------|
| `wait` | «Когда {title}.» |
| `do` | «Я {title}.» |
| `decide` | «{question} Если {label}: … Иначе: …» |
| `end` | «Задача завершена.» |
| ребро `loop` | «Возвращаюсь к «{title}».» |

---

## 10. YAML

Канон — `behavior`. Секция `execution:` отсутствует или помечена generated.

Импорт:

- документ с `behavior:` → граф, compile только preview/publish
- legacy FSM YAML (`states:` / `on:`) → lift

---

## 11. Код

| Слой | Путь |
|------|------|
| Спека | `docs/archive/BEHAVIOR_SPEC.md` |
| Backend | `backend/definition/behavior/` |
| Frontend | `frontend/src/features/skills/types/behavior.ts`, `utils/behavior*.ts` |
| Runtime mapper | игнорирует `behavior` / `origin*`; читает `states` |

---

## 12. Вне v1

Parallel, timeout/retry как узлы, богатый `input` (схема полей), редактирование FSM, вложенные `decide`, оптимистичный concurrency autosave.
