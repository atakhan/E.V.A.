# Жизнь заменяет рантайм (онтология)

> 2026-11-06. Онтологический поворот: несущий процесс агента — «Жизнь»; пакет `backend/runtime/` — машина исполнения. Плагин `runtime` в каталоге отложен.

## Инварианты

1. **Агент жив ⇔** есть навык `life` **и** ровно одна активная нить жизни (Skill Run `skill_id=life`, status `waiting`/`running`).
2. **«Жизнь» — глобальный FSM агента** (программа существования), не ещё один слушающий навык рядом с остальными.
3. **Остальные навыки — эпизоды:** отдельные Skill Runs с `parent_run_id` / `vars._life_run_id` → id нити жизни (не вложенный FSM в одном run).
4. **Машина** — `backend/runtime/` + worker/stores. Это не модель продукта. `kind: runtime` (агент проекта) — другое значение слова, не путать.
5. Внешние события пока могут стартовать эпизоды напрямую (текущий dispatcher). Маршрутизация «всё через жизнь» / tool `runtime.start_skill` — следующий слой.

```text
Жизнь (одна waiting-нить)
    ↑ обеспечивает ensure_life_run (publish + route)
Эпизоды (talk_to_*, work skills…)
    ↑ parent_run_id / _life_run_id
Машина backend/runtime
```

## Код

- Навык: [`backend/definition/system_skills.py`](../../backend/definition/system_skills.py) — состояние `alive`, без channel accepts; bootstrap `life.started`.
- Нить: [`backend/runtime/life.py`](../../backend/runtime/life.py) — `ensure_life_run_on_service` / `ensure_life_run_for_agent` / `attach_life_parent`.
- Крючки: `AgentService.publish`, `RuntimeService.route_all` + создание эпизода в `_resolve_targets`.
- Черновик манифеста инструмента: `backend/tools/runtime/` (`implemented: false`) — не обязателен для онтологии.

## Открыто на потом

- Пропуск всех событий только через FSM жизни.
- Реализация tool `runtime` и сужение ambient API.
- Rename UI/API «Runtime» → «Жизнь».
- Переименование `kind: runtime`.
