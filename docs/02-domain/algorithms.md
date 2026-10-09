# Algorithms — алгоритмы и формальные правила

> Уровень: **Как это вычисляется** (но ещё не код). Все алгоритмы восстановлены по коду и проверены unit-тестами проекта или прямым прогоном; где поведение противоречит спекам/шпаргалкам — отмечено.

## A1. Язык guard-условий

**Грамматика (Fact).** Ровно одно сравнение:

```text
guard   := path WS? op WS? right
path    := ident ('.' ident)*          // ident = [A-Za-z0-9_]+
op      := '==' | '!=' | '>=' | '<=' | '>' | '<'
right   := path-from-scope | literal
literal := true | false | null | "строка" | 'строка' | число (int/float) | слово
```

Пустой guard — истина. Строка, не подходящая под грамматику, — **ложь** при исполнении и ошибка `invalid_guard_syntax` при валидации. Логических связок (`and`/`or`) нет.

**Область видимости для guard перехода (Fact):**

| Префикс | Что это |
|---|---|
| `vars.*` | переменные run |
| `payload.*` | payload триггер-события |
| `event.*` | **тот же payload** (не конверт: `event.type`, `event.source` недоступны) |
| `result.*` | `payload.result` — результат операции в событии `action.<id>.completed` |
| `needs_clarification` | shorthand для `vars.needs_clarification` (legacy демо) |

Специальный сегмент `.length` возвращает длину списка/строки/словаря. Отсутствующий путь → `null`; сравнения `>`/`<` с `null` — ложь; `==`/`!=` сравнивают как есть (`null == null` истинно).

Правая часть, начинающаяся с `vars.`/`payload.`/`result.`/`event.`, разрешается как путь; иначе — литерал. Пример из сценария: `payload.conversation_id == vars.conversation_id`.

**Область видимости для `when` шага recipe (Fact, проверено прогоном).** Условие вычисляется тем же движком, но корень `vars` указывает на **scope шага** `{input, vars, steps, payload}`, а `payload` — на несистемные `vars` run. Следствие:

| Выражение в `when` | Результат |
|---|---|
| `vars.use_llm == true` | **ложь** (ищет `scope.use_llm`) — вопреки примеру в шпаргалке `.cursor/skills/eva-specs/actions.md` |
| `payload.use_llm == true` | работает (значение из vars run) |
| `vars.vars.use_llm == true` | работает |
| `vars.steps.s1.result.count > 1` | работает |
| `steps.s1.result.count > 1` | ложь |

Зафиксировано в [`REVIEW.md`](../REVIEW.md) как расхождение документации и кода.

## A2. Шаблоны в `input` шага

**Fact.** В строках заменяются `{{path}}`; корни: `input.*` (вход операции), `vars.*`, `steps.<id>.result.*`, `payload.*`. Отсутствующее значение → пустая строка; любое значение приводится к строке (число `0` → `"0"`). Legacy-форма `${vars.key}` поддерживается. Подстановка рекурсивна по словарям и спискам; нестроковые значения не трогаются.

## A3. Разрешение ссылки `tool` в инстанс

```text
resolve(ref):
  if ref == id инстанса агента:
      enabled → ok(instance)       else → disabled(instance)
  elif ref — id типа в каталоге:
      включённых инстансов этого типа == 1 → ok(тот инстанс)
      > 1                                   → ambiguous
      == 0 и ровно один выключенный         → disabled
      иначе                                 → unknown
  else → unknown
```

Используется и валидацией (ошибки `unknown_tool_instance`, `ambiguous_tool_reference`, `disabled_tool_instance`), и исполнением (ошибка операции при `ambiguous`/`disabled`/`unknown`). Фронтенд реализует тот же алгоритм поверх каталога, загруженного с сервера.

## A4. Выбор Skill для нового события

**Fact (вход через канал / worker).** Приоритет:

1. Явный `skillId` запроса — должен существовать у агента, иначе ошибка.
2. Ровно один Skill, чьё начальное состояние ждёт `event.type` → он.
3. Несколько таких → `defaultSkillId`, если он среди них; иначе ошибка «неоднозначно».
4. Ни одного → `defaultSkillId` агента, если задан.
5. Deprecated: переменная окружения `EVA_DEFAULT_SKILL_IDS` вида `slug=skill,…` (с предупреждением в лог).
6. Иначе — ошибка «ни один Skill не обрабатывает событие» (HTTP 422 на ingress; для `web.*` событий ingress всё равно принимает).

**Fact (внутри runtime при fan-out).** После неудачного поиска ждущих run стартуются **все** Skills, у которых начальное состояние ждёт `event.type`; если таких нет — Skill из контекста запроса.

## A5. Классификация акта диспетчером

Порядок проверок (Fact; регулярные выражения — по русским и английским словоформам):

```text
1. не человеческий акт (есть skill_run_id | action.* | runtime.continue) → pass_through
2. тип — жест (ui.request.parse_requested | human.request.reviewed) или intent ∈ {parse, parse_request, review, approve, confirm} при не-чат типе:
     есть рабочая run, ждущая этот тип → resume(она) ; иначе → start(скилл по типу)
3. тип ≠ channel.message.received → pass_through
4. текст ~ /стоп|stop|отмен|cancel|хватит|не надо/            → cancel (рабочие run по сущностям фокуса, иначе все) + чат
5. текст ~ /сначала|только|не трогай/ и есть рабочие run:
     нет сущностей → underspecified ; иначе → amend (= cancel всех рабочих + start parse по сущностям)
6. намерение parse (intent или /разбер|распарс|parse/):
     деиктика («это/этот/эти/ту…») без сущностей → underspecified
     есть рабочая run, ждущая parse → resume ; иначе → start (rewrite в ui.request.parse_requested)
7. намерение review (intent или /подтверд|одобр|approve|confirm/) или («да/ок/yes…» и есть рабочие run и сущности):
     ждущая review run (предпочтительно по сущностям) → resume ; иначе → start (rewrite в human.request.reviewed, decision=approve)
8. «нет/не то/no» и есть рабочие run → cancel (по сущностям) + чат
9. есть рабочая run, ждущая channel.message.received, и текст не вопрос (нет «?», не начинается с кто/что/где/когда/почему/зачем/сколько/как) → resume(она)
10. иначе → side_question → разговорный скилл (resume его ждущего run, если есть)
```

Сущности акта собираются из `entity_ids`, `entity_id`, `request_id`, фокуса (`selectedEntityIds`, `openEntityId`) и текста (`REQ-…`, `TG-…`).

## A6. Ключ блокировки события

```text
если известны conversation_id и skill_id → conv-skill:{conversation_id}:{skill_id}
иначе если есть skill_run_id            → run:{skill_run_id}
иначе если есть entity_id/request_id    → entity:{id}
иначе                                   → event:{event_id}
```

`skill_id` определяется до блокировки: из целевого run, из ждущего run разговора, из транспортного `skillId`, иначе по A4.

## A7. Валидация документа агента

Severity: `error` блокирует публикацию. Правила (Fact, сервер и UI совпадают по кодам):

| Код | Severity | Условие |
|---|---|---|
| `no_skills` | info | нет Skills |
| `invalid_default_skill` | error | `defaultSkillId` не найден |
| `skill_empty` | warning | нет состояний |
| `missing_initial` / `invalid_initial` | error | нет/битый `initial` |
| `unreachable_state` | warning | состояние недостижимо из `initial` |
| `dead_end_state` | warning | достижимое не-final состояние без переходов и `onEnter` |
| `empty_event` | warning | пустой `event` у перехода |
| `invalid_guard_syntax` | error | guard не соответствует A1 |
| `invalid_transition_target` | error | `to` неизвестен |
| `unknown_action` | error | `onEnter`/`actions` ссылаются на отсутствующий Action |
| `ambiguous_guards` | warning | несколько handler-ов одного event без guard |
| `invalid_skill_version` / `invalid_action_version` | warning | не SemVer |
| `empty_param_name` | warning | param без имени |
| `invalid_action_policy` | error | policy ∉ {auto, needs_human} |
| `empty_recipe` | warning | Action без шагов |
| `duplicate_step_id` | error | повтор id шага |
| `unknown_tool_instance` / `ambiguous_tool_reference` / `disabled_tool_instance` / `unknown_tool` / `unknown_command` | error | по A3 и каталогу |
| `invalid_step_input` | error / warning | вход шага не проходит схему команды (warning — неизвестные поля) |
| `unused_action` | info | Action не используется ни в одном Skill |
| `no_enabled_tools` | warning | есть recipe, но нет включённых инстансов |
| `missing_credential` | error | включённый инстанс `telegram` / `polza_ai_llm` / `web_client` без `credentialId` — **только сервер** |
| `duplicate_credential` | error | два инстанса `telegram` с одним credential — **только сервер** |

Достижимость считается обходом по `transitions[].to` от `initial`. Правила `missing_credential` и `duplicate_credential` есть только в серверной валидации; UI покажет их после `POST /validate` (Overview), но не в локальном отчёте.

## A8. Версия публикации

`X.Y.Z` → `X.Y.(Z+1)` от **последней по дате** публикации; если версия последней не SemVer — `0.1.0`. Версии Skill/Action внутри документа на версию публикации не влияют.

## A9. Повторы и временные ошибки

- Ошибка команды считается временной, если текст содержит `timeout`, `503`, `502`, `504`, `connection`, `temporarily`.
- Повтор команды только при временной ошибке и `attempt < max_attempts`; пауза `min(0.25·attempt, 2.0)` с.
- Повтор операции целиком — при любой ошибке до `max_attempts`; `max_attempts` берётся из `retry.max_attempts` (по умолчанию 1).
- Дедлайн операции проверяется **перед каждым шагом**, не прерывая текущий вызов.

## A10. Построение входа операции

```text
input = {
  request_id:      vars.request_id,
  message:         vars.last_message or vars.text,
  message_id:      vars.message_id,
  conversation_id: vars.conversation_id,
  + все vars без префикса '_' (не перекрывая перечисленные)
}
```

## A11. Снимок стола → vars

Если среди инструментов run есть `web_client` и событие не служебное: `get_snapshot` → `vars._desk` (объект), `vars._desk_text` (JSON ≤ 8000 символов). Если в снимке `workspace.requests[]` (или `requests[]`) есть запись с `id == vars.entity_id|request_id`, её поля `quantity`, `unit`, `title`, `status`, `site` перезаписывают одноимённые `vars`.

## A12. Санитизация логов

Ключи, равные `api_key`, `token`, `bot_token`, `secret`, `password`, `authorization`, `*_key`, `*_token` (без учёта регистра и `-`/`_`) → `***`; строки обрезаются до 4000 символов; списки — до 50 элементов; глубина — до 8.

## A13. Геометрия холста (frontend)

Ортогональная маршрутизация стрелок с обходом узлов, защитные зоны, внешний коридор для циклов, магнитные порты (сторона + якорь 0..1), автораскладка. Формальное описание — `docs_old/FSM_CANVAS_GEOMETRY.md` (актуально: код в `frontend/src/features/skills/utils/geometry/`, покрыт тестами `orthogonalRouting.test.ts`). Геометрия не влияет на исполнение: в публикацию уходят `states[]`, координаты — только для отрисовки.
