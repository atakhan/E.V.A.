# Конструктор Skills — модель работы

> Обзор: как устроен редактор скиллов.  
> Исполняемый контракт: [`SKILLS_SPEC_v0.1.md`](./SKILLS_SPEC_v0.1.md) + [`RUNTIME_SPEC_v0.1.md`](./RUNTIME_SPEC_v0.1.md).  
> Визуальный язык холста: [`FSM_CANVAS_STYLE.md`](./FSM_CANVAS_STYLE.md).  
> Геометрия и маршрутизация: [`FSM_CANVAS_GEOMETRY.md`](./FSM_CANVAS_GEOMETRY.md).

**Статус:** FSM — source of truth конструктора. Черновик и публикация — один и тот же автомат (`states[]`).

Ранний эксперимент с Behavior Graph / вкладкой «История» / компилятором на publish снят. Исторические заметки: [`archive/NEW_CONSTRUCTOR_DESC.md`](./archive/NEW_CONSTRUCTOR_DESC.md), [`archive/BEHAVIOR_SPEC.md`](./archive/BEHAVIOR_SPEC.md).

---

## 1. Что здесь происходит

Конструктор Skills — редактор **конечного автомата** одного скилла.

Человек рисует states и transitions. Runtime исполняет ровно этот автомат. Нет промежуточного графа «wait/do/decide» и нет шага compile между холстом и publication.

```text
человек рисует FSM на холсте
        ↓
 skill.states[] + initial + params   ← source of truth
        ↓  validate
 draft агента
        ↓  publish (as-is)
 immutable publication
        ↓
     Runtime
```

Skill отвечает на вопрос: **как агент решает этот класс задач?**

Skill **не** вызывает Tools:

```text
Tool        — техническая способность   (telegram.send_message)
Action      — операция / рецепт          (parse_request)
Skill / FSM — процесс                    (process_foreman_request)
```

```text
Event → Dispatcher → FSM → Action → Tool → World → Event
```

FSM ссылается только на **id Action**.

---

## 2. Холст

Маршрут: `/:slug/skills` → `/:slug/skills/:skillId`.

Инструменты:

| Инструмент | Смысл |
|------------|--------|
| Выбор | выделить state / transition, двигать, ресайзить |
| State | нарисовать состояние |
| Transition | клик на стороне источника → клик на стороне цели |
| Раскладка | Auto-layout узлов; маршруты пересчитываются отдельно |

Инспектор справа:

- ничего не выбрано — version, описание, params, initial;
- state — имя, id, `on_enter`, `final`;
- transition — event, guard, actions, `to`.

YAML↓ / YAML↑ экспортирует канон FSM (`states` / `on` / `on_enter`), не граф поведения и не SVG-маршруты.

Связи на холсте — смысловые переходы. Их геометрию считает маршрутизатор: ортогональный обход узлов, защитные зоны, внешний коридор для циклов. Пользователь двигает состояния; стрелки не правятся вручную по сегментам. Подробности: [`FSM_CANVAS_GEOMETRY.md`](./FSM_CANVAS_GEOMETRY.md).

Живые Skill Run смотрят в разделе Runtime агента (`/:slug/runtime`), не отдельной вкладкой холста.

---

## 3. Канон skill

```yaml
id: process_foreman_request
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
        actions: [ingest_channel_message]
        to: analyzing

  analyzing:
    on:
      action.parse_request.completed:
        - guard: "result.missing_fields.length == 0"
          to: ready_for_review
        - guard: "result.missing_fields.length > 0"
          actions: [clarify_with_foreman]
          to: waiting_for_foreman

  waiting_for_foreman:
    on:
      channel.message.received:
        actions: [parse_foreman_response]
        to: analyzing

  completed:
    final: true
```

Правила — [`SKILLS_SPEC_v0.1.md`](./SKILLS_SPEC_v0.1.md):

- один FSM на skill, один `initial`;
- handler: `event` → optional `guard` → `actions[]` → `to`;
- несколько handler'ов одного event — по порядку, детерминированно;
- `final: true` завершает Skill Run;
- «жду следующее событие» — обычный state, не `final`;
- `on_enter` выполняется при входе в state;
- guards: `result.*`, `event.*`, `payload.*`, `vars.*`; операторы `== != >= <= > <` и `.length`;
- completion Action: `action.<action_id>.completed`.

---

## 4. Draft и publish

Черновик сохраняет `states[]` как есть.

Publish не компилирует и не переписывает id состояний. Отклоняется только если `validate_agent` вернул errors.

Runtime читает **publication**, не draft.

---

## 5. Валидация (конструктор)

| Код | Severity | Когда |
|-----|----------|--------|
| `skill_empty` | warning | нет states |
| `missing_initial` / `invalid_initial` | error | нет / битый initial |
| `unreachable_state` | warning | state недостижим из initial |
| `dead_end_state` | warning | не-final без переходов |
| `empty_event` | warning | пустой event |
| `invalid_guard_syntax` | error | guard не проходит безопасный синтаксис |
| `invalid_transition_target` | error | `to` неизвестен |
| `unknown_action` | error | action нет в каталоге агента |
| `ambiguous_guards` | warning | несколько handlers одного event без guard |
| `invalid_skill_version` | warning | version не SemVer `X.Y.Z` |
| `empty_param_name` | warning | param без имени |

---

## 6. Миграция старых черновиков

Документы, у которых ещё лежит `behavior` (граф wait/do/decide), при загрузке и сохранении **один раз** превращаются в `states[]`. Компилятор остаётся только как этот flatten, не как шаг редактирования.

Если compile графа не удался, остаются уже лежащие `states[]` (если они были).

---

## 7. Карта кода

| Слой | Путь |
|------|------|
| Холст / инспектор | `FsmCanvas.vue`, `SkillInspector.vue`, `CanvasToolbar.vue` |
| Геометрия / routing | `frontend/src/features/skills/utils/geometry/` |
| Типы | `frontend/src/features/skills/types/skill.ts`, `fsm.ts` |
| YAML | `utils/skillYaml.ts` |
| Validation | `utils/validateSkill.ts`, `backend/definition/validation/validate_skill.py` |
| Runtime FSM | `backend/runtime/fsm_engine.py`, `skill_runner.py` |
| Flatten leftover graph | `backend/definition/behavior/materialize.py`, `frontend` `normalizeSkill` |
