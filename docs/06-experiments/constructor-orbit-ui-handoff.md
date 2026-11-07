# Handoff: конструктор, орбиты, иконки агентов

> Контекст для нового чата Cursor (после `bcf3975`, 2026-11-06).  
> Цель следующего этапа: **строить интерфейс вокруг иконок агентов и их орбит**, не ломая пространственную лестницу режимов.

## Как стартовать новый чат

В первое сообщение приложи этот файл (`@docs/06-experiments/constructor-orbit-ui-handoff.md`) и коротко скажи задачу, например:

> Продолжаем UI вокруг орбит агентов. Сначала прочитай handoff и принципы; не ломай one-pass / handoff.

AlwaysApply уже подтягивают:

- [`.cursor/rules/spatial-ui-design.mdc`](../../.cursor/rules/spatial-ui-design.mdc)
- [`.cursor/rules/collaboration.mdc`](../../.cursor/rules/collaboration.mdc)

Skill (читай при работе над столами/орбитами): [`.cursor/skills/eva-spatial-ui/SKILL.md`](../../.cursor/skills/eva-spatial-ui/SKILL.md).

---

## Где мы сейчас (Fact)

### Лестница режимов (один маршрут)

`/projects` → `/projects/:projectSlug` → `/projects/:projectSlug/:agentSlug`  
Ева: `/projects/eva` (платформенный агент `kind: platform`, slug `eva`).

| Режим | Центр | Сателлиты на орбите |
|-------|--------|---------------------|
| Стол Евы | Ева | проекты на внешней орбите; «Новый» (серый) на внутренней, ближе к Еве |
| Конструктор Евы | hub `eva` | каналы / мир |
| Стол проекта | runtime проекта | агенты проекта |
| Конструктор агента | hub агента | каналы, skills, plugins… |
| Канал / слой | карточка канала или action | адреса / дуга действий |
| Память | карточка памяти | о себе / жизнь / вехи / задачи / другие / навыки / внимание (`memoryOrbit`, [`memory-constructor-draft.md`](./memory-constructor-draft.md)); слой полки → центр + карточки справа ([`constructor-memory-retrospective.md`](./constructor-memory-retrospective.md)) |
| Плагин | instance в **левой половине**, у средней линии с gutter; детали — столбец справа от линии (`layoutPluginColumn`), подписи **справа от иконок**; фасет → hub + **reading stage**; выход только Escape / «назад» |
| Навык | та же раскладка, что у плагина (`layoutSkillHubPose` / `layoutSkillColumn`); фасеты: о себе / состояния / нужно; reading stage; Escape / «назад» |

Метафора: **масштаб одного стола**, не набор страниц. Канон ощущения: [`../01-concept/spatial-ui-principles.md`](../01-concept/spatial-ui-principles.md).  
Фон модели: [`../01-concept/spatial-model.md`](../01-concept/spatial-model.md).  
Ретро процесса: [`constructor-spatial-modes-retrospective.md`](./constructor-spatial-modes-retrospective.md).

### Что уже сделано в коде (коммит `bcf3975`)

- **One-pass motion** на Eva↔constructor, Eva↔project, project↔agent; channel/layer на том же `useDeskMotion`.
- **Packed orbit** — общий алгоритм `packedOrbit.ts`, тонкие обёртки hub/runtime.
- **Motion API** — `features/projects/motion/` (`useDeskMotion`, `handoffSeat`/`runHandoff`, `DeskPass`, `LeaveHold`, `Flight`).
- **Orbit UI helpers** — `orbitStyles.ts` → `ProjectsDesk` / `ProjectDesk` (не полный merge в `OrbitBoard`).
- **Measure** — `defineExpose({ rootEl })` с desk-компонентов; Escape по `[data-channel-mode]` ещё через `querySelector`.
- **Документы + rules** — принципы, ретро, collaboration / spatial-ui-design.

### Карта файлов (куда лезть)

```text
frontend/src/features/projects/
  motion/           # token, wait/frame, handoff, DeskPass, LeaveHold
  utils/
    packedOrbit.ts  # алгоритм орбиты + тесты
    projectsHubLayout.ts / deskLayout.ts  # константы hub vs runtime
    orbitStyles.ts  # place/icon style (collapse, focus-exempt, flight)
    deskMotion.ts   # DESK_MOVE_MS, ease, reveal/aside
  components/
    ProjectsDesk.vue   # орбита проектов вокруг Евы
    ProjectDesk.vue    # орбита агентов вокруг runtime
  views/
    ProjectsListView.vue   # хаб Евы + leave-hold проекта
    ProjectDeskView.vue    # стол проекта ↔ конструктор агента

frontend/src/features/constructor/
  views/ConstructorView.vue          # hub агента, channel/layer passes
  components/InfiniteCanvas.vue      # стол мира
  components/AgentHubCard.vue        # центр конструктора
```

Роутинг: `frontend/src/router/paths.ts` (`evaConstructorPath`, `isEvaConstructorSlug`).  
Backend Евы: `ensure_eva_agent`, `kind: platform` в `agent_service.py`.

---

## Опыт чата — как работать с владельцем

Владелец говорит **локальными симптомами** («дергается», «копия в конечной точке», «блик») + иногда **желаемой физикой**. Не ждать абстрактного ТЗ.

1. **Сначала инвариант / принцип**, потом многошаговый UX. Если переход сложный — назвать one-pass / handoff до кода.
2. **Минимальный diff + соседняя проверка** (обратный переход, соседний режим, twin / blank / focus-in-collapse).
3. **Сравни два существующих решения → reuse**, не изобретай третью орбиту/тайминг.
4. **Один concern за проход** — не мешать «новую фичу иконки» с «переписать все тайминги».
5. **Закрывать в языке симптома**, не рефактор-нарративом.
6. **Коммит только по просьбе.**

### Антипаттерны, которые уже жгли круги

- Sequential `await`: collapse → fly → reveal
- Фокусный flyer схлопнут с сателлитами
- Цель на сиденье видна до прилёта / opacity fade на handoff
- Twin (две иконки на одном месте)
- Stretch орбиты «заполнить дугу» вместо packed min-chord
- Глобальный `querySelector` для measure (кроме осознанных гейтов)

---

## Куда строить дальше (следующий чат)

### Продуктовый фокус

**Интерфейс вокруг иконок агентов и их орбит** — chrome, действия, статусы, плотность, жесты у сателлитов/центра, не ломая лестницу масштабов.

Опирайся на уже работающие паттерны:

- packed placement + `orbitPlaceStyle` / `orbitIconStyle`
- burst из центра / collapse в центр
- focus-exempt во время полёта
- handoff snap без fade

### Возможные направления (не заказ — ориентиры)

- UI у иконки на орбите (меню, статус, connect/remove без «карточного дашборда»)
- Более богатый chrome стола при сохранении «один центр + орбита»
- Состояния орбиты (пустая, dense, focus) без новой метафоры раскладки
- Сближение channel-satellites с desk-orbit helpers, если появится дублирование
- Опционально позже: `OrbitBoard.vue`, тёплый `ConstructorView`, perf по профилю

### Не трогать без нужды

- Channel motion в ConstructorView уже на `useDeskMotion` — не переписывать «заодно»
- Не возвращать `hubClear`-булевы комбайны — есть `DeskPass`
- Не размазывать орбиту ради «воздуха»

---

## Приёмка любой правки орбиты / перехода

Туда и обратно для затронутого режима (чеклист из principles):

- [ ] Один заход, не фазы `await`
- [ ] Нет twin / пустого кадра / блика opacity
- [ ] Фокус не в collapse mid-flight
- [ ] Сателлиты из центра / в центр, не мигают на орбите

Техпроверка: `cd frontend && npx vue-tsc --noEmit` и vitest на `packedOrbit` / `motion` при изменениях layout/handoff.

---

## Хвост долга (низкий приоритет)

- Escape `[data-channel-mode]` ещё через `document.querySelector`
- Views всё ещё толстые (stage + measure + routing) — дальше выносить только по боли
- Полный merge desks → `OrbitBoard` — только если helper’ов мало
- Ретро §6 частично устарела: motion/layout/handoff/leaveHold/commit уже сделаны; оставлять как историю процесса
