# FSM Canvas Style Guide (UML-lite)

> Визуальный язык холста Skill FSM в E.V.A. Основан на **UML State Machine** (Harel statecharts), упрощён под v0.1 модель Skills.

## Цель

Схема должна читаться без Inspector: **где мы**, **что ждём**, **что делаем**, **куда идём**.

## Элементы

### State (прямоугольник)

| Элемент | Отображение | Данные |
|---------|-------------|--------|
| Имя | Крупная подпись в блоке | `name` (fallback: `id`) |
| Технический id | Мелкий mono при выборе | `id` |
| Entry | `entry / action1, action2` | `onEnter[]` |
| Final | Иконка «мишень» в углу блока | `final: true` |

**Не** помечаем `initial` внутри блока — для старта используется псевдо-состояние (см. ниже).

### Initial (псевдо-состояние)

- Заполненный круг слева от initial state
- Стрелка от круга к левому краю state
- Один на Skill (`model.initial`)

### Final (псевдо-состояние)

- Двойной круг (bullseye) внутри state — UML final
- Не отдельный блок на холсте (в v0.1)

### Transition (стрелка)

Подпись в формате UML:

```text
event [guard] / action1, action2
```

| Часть | Источник | Правило отображения |
|-------|----------|---------------------|
| `event` | `transition.event` | Всегда, строка 1 |
| `[guard]` | `transition.guard` | Если не пустой; усечение вне выбора |
| `/ actions` | `transition.actions` | Если не пустой; строка 2 |

Длинные списки actions: `a, b +2`.

### Поток

- Предпочтительно **слева направо** или **сверху вниз**
- Self-loop — допустим (ожидание в том же state)

## Соответствие SKILLS_SPEC v0.1

```text
Skill → FSM → Action → Tool
```

FSM ссылается только на **Action id**, не на Tool commands.

## Вне scope (позже)

- `exit`, `do` activity
- Choice / junction pseudostates
- Composite (nested) states
- Orthogonal regions

## Файлы реализации

- Холст: `frontend/src/features/skills/components/FsmCanvas.vue`
- Подписи: `frontend/src/features/skills/utils/edgeRouting.ts`
- Модель: `frontend/src/features/skills/types/fsm.ts`
