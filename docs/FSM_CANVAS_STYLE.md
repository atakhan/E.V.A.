# FSM / Behavior Canvas Style Guide

> Визуальный язык конструктора поведения в E.V.A.

Канон модели: [`BEHAVIOR_SPEC.md`](./BEHAVIOR_SPEC.md).  
Исполняемая FSM: [`SKILLS_SPEC_v0.1.md`](./SKILLS_SPEC_v0.1.md).

## Принцип

Canvas по умолчанию отвечает на вопрос **«что делает агент?»**, не «какие states в FSM?».

- **История** — карточки wait / do / decide / end. Редактор Behavior Graph.
- **Логика** — тот же граф, технические id / event / guard. Редактор Behavior Graph.
- **Runtime** — подсветка шагов по `originNodeId`. Без редактирования.
- **Машина** — скомпилированная FSM. Read-only.

FSM — artifact (`execution.states`), не source of truth.

## Карточки (Story)

- **wait** — «Когда…» / «Жду…»
- **do** — человеческое имя Action, мелкий `actionId`
- **decide** — вопрос + ветки Да/Нет
- **end** — только «задача завершена». Цикл «жду следующее сообщение» — `wait`.

## Файлы

- Холст: `frontend/src/features/skills/components/BehaviorCanvas.vue`
- Инспектор: `frontend/src/features/skills/components/BehaviorInspector.vue`
- Компилятор: `frontend/src/features/skills/utils/behaviorCompile.ts`, `backend/definition/behavior/`
- Legacy UML canvas: `frontend/src/features/skills/components/FsmCanvas.vue`
