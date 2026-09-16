# FSM Canvas Style Guide

> Визуальный язык конструктора Skills в E.V.A.

Канон конструктора: [`SKILLS_CONSTRUCTOR.md`](./SKILLS_CONSTRUCTOR.md).  
Исполняемая FSM: [`SKILLS_SPEC_v0.1.md`](./SKILLS_SPEC_v0.1.md).  
Геометрия и маршрутизация: [`FSM_CANVAS_GEOMETRY.md`](./FSM_CANVAS_GEOMETRY.md).

## Принцип

Холст — редактор автомата. Source of truth — `states[]`. Что нарисовано, то уходит в publish и runtime.

- **State** — прямоугольник: id, необязательное человеческое имя, `on_enter`, `final`.
- **Transition** — стрелка: event, optional guard, `actions[]`, `to`.
- UML-подписи на рёбрах, магнитные порты, ортогональная маршрутизация вокруг узлов, ресайз states.

## Файлы

- Холст: `frontend/src/features/skills/components/FsmCanvas.vue`
- Геометрия: `frontend/src/features/skills/utils/geometry/`
- Инспектор: `frontend/src/features/skills/components/SkillInspector.vue`
- Тулбар: `frontend/src/features/skills/components/CanvasToolbar.vue`
