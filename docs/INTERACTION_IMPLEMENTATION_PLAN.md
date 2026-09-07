# План: слой взаимодействия (диспетчер, сессия ≠ работа)

> Статус: фазы 0–5 сделаны в коде (с оговорками в заметках). Диспетчер — таблица, не LLM. «Сделано» = код смержен, не приёмка §16.  
> Канон требований — [`INTERACTION_SPEC_v0.1.md`](./INTERACTION_SPEC_v0.1.md).  
> Критика хода работ — [`INTERACTION_IMPLEMENTATION_NOTES.md`](./INTERACTION_IMPLEMENTATION_NOTES.md).  
> Синтез заметок — [`INTERACTION_NOTES_ARCHITECTURE_REVIEW.md`](./INTERACTION_NOTES_ARCHITECTURE_REVIEW.md).

## Цель

Чтобы веб-клиент с чатом **и** кнопками ощущался одним коллегой за столом.

Сейчас исполнение одной работы (Skill → Action → Tool, Behavior Graph) подходит. Ломается слой **над** скиллом: ждущий run забирает всю сессию, фраза и жест — два агента, стол агент не читает.

Приёмка — шесть вопросов из INTERACTION §16. После фазы 4–5: 1 и 3 = да; 2 = да для «разбери» + фокус/объект (таблица, не NLU); 4 = частично («да» закрывает review wait); 5 = да, если в фокусе есть entity (иначе underspecified); 6 = факт `web.state.changed` уходит, речь новой цифры — со следующего ответа после чтения стола.

## Что не трогаем

- Конструктор, компилятор Behavior Graph, `states[]` как execution artifact
- ACTIONS / TOOLS / политика recipe
- Модель «Event = факт», «Skill не зовёт Tool»
- Runtime как ERP (стол остаётся в веб-клиенте)

Не в том же заходе: NLU-роутер внутри `razgovor`, единый скилл «на всё», переписывание ai_supplier CRM.

## Канон документов (фаза 0, до кода)

Сейчас INTERACTION — target, RUNTIME §15 — норма исполнения. Код слушает RUNTIME. Пока оба живы, любой PR «починить pin» спорит со спекой.

Сделать:

1. **INTERACTION_SPEC** — статус: норматив слоя «акт человека → работа». Не черновик «над» runtime.
2. **RUNTIME_SPEC** — errata §15, §18–20, §22:
   - resume waiting-run по `conversation_id` **только** если текущее состояние явно ждёт этот `event.type` (или акт помечен как ответ этой работе);
   - иначе — новый run / другой скилл, waiting не владеет сессией;
   - нет перехода ≠ `SkillRun.error`; no-match пропускается;
   - 1 `conversation_id` → 0..N живых run;
   - correlation lock на `skill_run_id` (или сущность), не на весь разговор.
3. **EVENT_SPEC** — envelope: `actor_id`; `focus` на акте (не в correlation «навсегда»); явно: `conversation_id` — адрес голоса, не ключ владения FSM.
4. **ARCHITECTURE_DOCS_ALIGNMENT** decision #1 — одно правило, без колонки «v0.1 vs target».
5. **Web Client** — короткий контракт акта (можно секция в INTERACTION §14, не отдельный роман): жест несёт `intent` + `entity_ids`; фраза — `text` + `focus`; `skillId` опциональная подсказка, не единственный диспетчер.

Порядок правки спек: alignment + RUNTIME/EVENT errata в одном коммите документации, затем код фазы 1. Не наоборот.

## Фазы кода

### Фаза 1 — разнять сессию (P0)

**Статус:** сделано в коде (`skill_routing.waiting_runs_matching_event`, worker pin, `_resolve_targets`, SkillRunner no-match). Тесты: `tests/test_interaction_routing.py`.

**Зачем:** клик не глотается чатом; чат не убивает разбор. Без NLU.

**Код:** `runtime_worker.py` (`find_waiting_by_conversation` не перекрывает чужой `event.type` / транспортный `skillId`), `runtime_service._resolve_targets`, `skill_runner._step` (no-match не error), `skill_handles_event_in_state` начать использовать.

**Тесты:**  
- waiting `razgovor` + `ui.request.parse_requested` → стартует рабочий скилл, чат остаётся waiting;  
- waiting parse + `channel.message.received` → чат-скилл, parse не error;  
- waiting run + тот же event type, который state ждёт → resume как сейчас.

**Приёмка:** вопрос 3 = да; вопрос 1 частично (события не убивают чужой run).

### Фаза 2 — N работ на разговоре

**Статус:** сделано в коде (`runtime/event_lock.py`, worker `_lock_key_for_event`, InMemory `by_conversation` = список, `GET /runs/by-conversation` → `items[]`). Тесты: lock keys + два waiting run в `tests/test_interaction_routing.py`.

**Зачем:** вопрос мимоходом и пакетный разбор сосуществуют. Lock не сериализует всю сессию как одного владельца.

**Код:** ключ lock = `conv-skill:{conversation}:{skill}` когда оба известны (не чистый `skill_run_id` — иначе два чата форкают `razgovor`, пока первый в THINKING). Postgres `find_waiting_runs` уже возвращает все active; API больше не сводит к «последний». InMemory `by_conversation` — список.

**Приёмка:** вопрос 1 = да на уровне «не срывает». Ответ «кто по арматуре?» может ещё идти в default-скилл, это ок. Два run *одного* скилла на нити по-прежнему сериализуются.

### Фаза 3 — контракт акта (фокус / жест)

**Статус:** сделано (`web_act.normalize_web_act`, `WebEventRequest` actor/focus/intent/entityIds, `enqueue_channel_event` кладёт focus в metadata и actor в `correlation.user_id`; ai_supplier чат и dispatch шлют те же поля). Тесты: `tests/test_web_act.py`.

**Зачем:** «это», кнопка = структурированное намерение.

**Код:** web ingress + `WebEventRequest`: `actor_id`, `focus`, для жеста `intent` + `entity_ids`. Пробросить в payload/metadata, не терять в `enqueue_channel_event`. ai_supplier: чат и `dispatchEvaEvent` шлют фокус/объект; `skillId` можно оставить как подсказку.

**Приёмка:** вопрос 2 **ещё нет** (нет диспетчера), но объект с кнопки стабильно в payload, «это» из фокуса доступно скиллу.

### Фаза 4 — диспетчер классов

**Статус:** сделано (`runtime/dispatcher.py` `classify_act` перед `_resolve_targets`; worker готовит event до lock). Тесты: `tests/test_dispatcher.py`.

**Зачем:** фраза «разбери» и кнопка — одна семья работ; «да» закрывает тот же wait.

**Код:** слой перед `_resolve_targets` (не внутри `razgovor`): resume / amend / start / мимо / cancel / недоопределено. v1 — таблица (тип события + фокус + открытые wait + ключевые слова), без LLM.

**Приёмка:** вопрос 2 = да при фокусе/entity; 4 = частично («да» → `human.request.reviewed`); 5 = amend как cancel + start с `entity_ids` из фокуса.

### Фаза 5 — стол и эффекты

**Статус:** сделано частично-честно: `refresh_desk_snapshot` в `_route_single`; `get_snapshot` в seed-рецептах; PATCH карточки → `web.state.changed`; `send_message` несёт `workspace_update`, `ui_proposal`, `presence`; ai_supplier рисует бейджи присутствия. Живой агент в БД увидит новые рецепты только после republish.

**Зачем:** агент говорит правду карточки; поручение двигает мир.

**Приёмка:** вопрос 6 = факт на проводе; речь новой цифры — со следующего ответа, если промпт видит `_desk_text`. R5.2 presence — на исходящем сообщении и в UI чата.

## Порядок PR (предлагаемый)

| PR | Содержание | Можно мержить отдельно |
|----|------------|------------------------|
| 0 | Errata спек + этот план в оглавлении | да | сделано |
| 1 | Pin + no-match + тесты | да, ценность сразу | сделано |
| 2 | N run + lock | да | сделано |
| 3 | Поля акта на ingress + ai_supplier | да | сделано |
| 4 | Диспетчер | зависит от 1–3 | сделано |
| 5 | Snapshot / effects / presence | зависит от 3–4 | сделано |

Не смешивать PR 0 с PR 1 в одном коммите «заодно поправим код» — тогда снова разъедется канон.

## Критерий «можно остановиться»

После фазы 1–2 система уже честнее текущей: два входа на одной сессии не убивают друг друга и не делят один lock. Гладкость из кейсов 4–6 начинается с фазы 4–5. Не надо ждать фазы 5, чтобы мержить 1–2.

## Связанные файлы

| Документ / код | Роль |
|----------------|------|
| [`INTERACTION_SPEC_v0.1.md`](./INTERACTION_SPEC_v0.1.md) | Требования |
| [`INTERACTION_NOTES_ARCHITECTURE_REVIEW.md`](./INTERACTION_NOTES_ARCHITECTURE_REVIEW.md) | Синтез заметок: control plane vs коллега |
| [`INTERACTION_OFFICE_MODEL.md`](./INTERACTION_OFFICE_MODEL.md) | Директор / стойка / бюро — язык стыка |
| [`INTERACTION_BUREAU_MODEL.md`](./INTERACTION_BUREAU_MODEL.md) | Гипотетическая конституция этажа бюро |
| [`INTERACTION_WORLD_MODEL.md`](./INTERACTION_WORLD_MODEL.md) | Три проекции ситуации: оператор, домен, агентство |
| [`RUNTIME_SPEC_v0.1.md`](./RUNTIME_SPEC_v0.1.md) §15, 18–20 | Errata routing |
| [`EVENT_SPEC_v0.1.md`](./EVENT_SPEC_v0.1.md) envelope, §21 | Акт, fan-out |
| [`ARCHITECTURE_DOCS_ALIGNMENT.md`](./ARCHITECTURE_DOCS_ALIGNMENT.md) | Одно решение #1 |
| `backend/workers/runtime_worker.py` | Pin + lock key |
| `backend/runtime/event_lock.py` | `conv-skill` / `run` / entity |
| `backend/runtime/runtime_service.py` | `_resolve_targets` |
| `backend/runtime/skill_runner.py` | no-match |
| `backend/runtime/dispatcher.py` | Классификация акта |
| `backend/runtime/desk.py` | Снимок стола в vars |
| `backend/runtime/presence.py` | Присутствие живых run |
| `backend/app/api/channels/web.py` | Контракт акта |
| `backend/app/api/channels/web_act.py` | normalize actor/focus/intent |
| `backend/tools/web_client/` | Snapshot / outbound |
