# Decisions — архитектурные и концептуальные решения

> Записи восстановлены из `architecture/*.md`, `docs_old/ARCHITECTURE_DOCS_ALIGNMENT.md` (decision log), спек, комментариев в коде и git history. Причины приводятся только если они зафиксированы в источниках; иначе — «Причина решения не установлена по доступным материалам». Формат: Context → Alternatives → Decision → Reason → Consequences.

| # | Решение | Источник | Статус |
|---|---|---|---|
| D1 | Конструктор агентов вместо одного «ИИ снабженца» | agent_architecture §1, итог | действует |
| D2 | Ядро модели: Tool → Action → Skill → Agent; FSM как язык Skill | agent_architecture §2–§4, §24–§28 | действует |
| D3 | Модульный монолит + workers, не микросервисы | backend_architecture §2 | действует |
| D4 | Python / FastAPI / PostgreSQL / Redis Streams; собственный FSM-runtime, не Temporal | backend_architecture §3, §17–§18, §26 | действует |
| D5 | FSM `states[]` — единственный source of truth конструктора; Behavior Graph снят | SKILLS_CONSTRUCTOR, коммиты 4d2ae2a→4dea5f0 | действует |
| D6 | Action Recipe — декларативные `steps[]`, не Python-код | backend_architecture §12, ACTIONS_SPEC | действует |
| D7 | Tool Type ≠ Tool Instance; recipe ссылается на инстанс | TOOLS_SDK §39, alignment #14 | действует |
| D8 | Event — факт, не команда; completion `action.<id>.completed` | EVENT_SPEC, alignment «Action completion trigger» | действует, нарушен rewrite |
| D9 | LLM — Tool в recipe; LLM не выбирает Action в FSM | alignment #5–#6 | действует |
| D10 | Иммутабельные публикации + пин версии на run | RUNTIME §4, коммит 7b56efe/статус P0 | действует |
| D11 | Разговор ≠ Skill Run: resume только если состояние ждёт event.type | INTERACTION R4.2, план фаза 1 | действует |
| D12 | Lock `conv-skill:{conversation}:{skill}` | RUNTIME §18, план фаза 2 | действует |
| D13 | Диспетчер актов — таблица правил перед FSM, без LLM/NLU | INTERACTION §7, план фаза 4 | действует (v1) |
| D14 | Стол (мир) живёт во внешнем веб-клиенте; runtime не ERP | INTERACTION R1.4, RUNTIME §2 | действует |
| D15 | Маршрутизация по документу агента (`defaultSkillId`, initial-переходы), env-карта deprecated | коммит 77c5d78 | действует |
| D16 | Каталог Tools — только на сервере; UI грузит `GET /api/tools/catalog` | TOOLS cheatsheet, коммит b8d1562 | действует |
| D17 | Секреты stage/prod — Infisical, не `.env` на сервере | коммиты defce8a, cc85371 | действует |
| D18 | Настройки без значений по умолчанию | коммит e4093bc | действует |
| D19 | `create_all` + `ALTER IF NOT EXISTS` вместо Alembic-ревизий | app/deps.py, alembic/env.py | действует |
| D20 | Нет сущностей Session / Context Manager / Task Manager | agent_architecture §16–§18 | действует |
| D21 | Planner вне scope v0.1 | agent_architecture §23, §29 | открыт |
| D22 | Валидация публикации блокирует только `error` | AgentService.publish | действует |
| D23 | Архивация агента вместо удаления как основной сценарий; активные run отменяются | AGENT_ARCHIVING_PLAN, коммит 10e2c84 | действует |

---

## D1. Конструктор агентов вместо одного «ИИ снабженца»

**Context.** Проектировался конкретный агент снабжения (прораб → заявка → уточнение → каталог → поставщики). Значительная часть архитектуры оказалась не про снабжение.
**Alternatives.** (a) Довести специализированного агента; (b) выделить универсальный конструктор, где снабженец — первый агент.
**Decision.** (b). «Человек проектирует поведение агента, а runtime исполняет это поведение.»
**Reason.** Зафиксирована в `agent_architecture_v1.md` §1 и итоге: архитектура агента в основном универсальна; универсальность проверяется тем, что рефлексия и другие процессы выражаются тем же конструктором (§22, §30).
**Consequences.** Снабженческие сущности не входят в ядро (только в сценарии/каталог как примеры); появился критерий проверки «три процесса без спец-сущностей» (не закрыт — E4).

## D2. Ядро: Tool → Action → Skill → Agent; FSM как язык Skill

**Context.** Нужна компактная модель, которую человек может рисовать, а машина — исполнять.
**Alternatives.** Рассмотрены и отвергнуты как отдельные сущности конструктора: Transition, FSM Engine, Event Router, Event Bus, Action Executor, Tool Executor, LLM Engine, Logs Manager, Session, Context, Memory-как-сущность, Entity Graph (§4, §16–§21).
**Decision.** Пять понятий: Tool (умеет), Action (делает), Skill (как решает), State (где), Event (что произошло). FSM — способ описать управление процессом Skill; переход — часть описания состояния, не сущность.
**Reason.** Уменьшение числа сущностей упрощает конструктор (§4); инфраструктурные модули не должны перегружать концептуальную модель (§16).
**Consequences.** Всё «инфраструктурное» живёт в runtime как реализация; Memory/Context/Entity Graph — Tools; Reflection — обычный Skill (гипотеза).

## D3. Модульный монолит + workers

**Context.** Соблазн разнести agent/skill/fsm/action/tool/event по сервисам.
**Alternatives.** Микросервисы; монолит.
**Decision.** Один backend (`domain/definition/runtime/infrastructure/tools`) + отдельные worker-процессы из того же образа.
**Reason.** Сущности слишком тесно связаны (Skill → FSM → Action → Tool), разносить по сети на раннем этапе искусственно (`backend_architecture_v1.md` §2).
**Consequences.** Один Docker-образ, три `command`; общая кодовая база; масштабирование — репликами процессов (не реализовано: один consumer).

## D4. Python / FastAPI / PostgreSQL / Redis Streams; собственный FSM-runtime

**Context.** Выбор стека для runtime и транспорта событий.
**Alternatives.** Temporal (durable workflows), NATS JetStream / Kafka, Kubernetes; другие языки.
**Decision.** Python 3.12 + FastAPI + SQLAlchemy/Postgres + Redis Streams; FSM-интерпретатор свой; Vue 3 на фронтенде.
**Reason.** Python: LLM-экосистема, Pydantic, удобство DSL/JSON Schema (§3). Redis Streams: прост, обычно уже есть, достаточно для MVP, заменим без смены домена (§17). Temporal — не в центре, т.к. FSM динамически создаётся пользователем; возможен позже как компилятор (§18). «Не Kubernetes, не микросервисы, не Kafka, не Temporal на первом этапе» (§26).
**Consequences.** Собственная реализация ожидания, дедупа, lock, DLQ, retry (RUNTIME §16–§28) — частично, с известными пробелами (REVIEW).

## D5. FSM `states[]` — единственный source of truth; Behavior Graph снят

**Context.** Эксперимент E1: Behavior Graph (wait/do/decide) + Story/Logic проекции + compile на publish.
**Alternatives.** (A) FSM → Story projection; (B) Story как источник; (В) семантическая модель + две проекции (выбран в эксперименте).
**Decision.** Вернуться к FSM как единственному источнику; publish as-is без compile; компилятор остаётся только для одноразового flatten старых черновиков.
**Reason.** Зафиксировано как факт решения (`SKILLS_CONSTRUCTOR.md`: «эксперимент снят»; коммит 4dea5f0). Конкретные аргументы: **причина решения не установлена по доступным материалам** (в документах нет записи «почему»). Inference: второй источник истины и шаг compile противоречили принципу «что нарисовано — то исполняется».
**Consequences.** Канон: холст редактирует `states[]`; остатки Behavior-кода и тесты сохранены как legacy (REVIEW).

## D6. Action Recipe — декларативные шаги

**Context.** Как описывать операцию агента: кодом или данными.
**Alternatives.** Python-функции; YAML/JSON `steps[]`.
**Decision.** `recipe: [{id, tool, command, input, when}]`; шаблоны `{{input.*}}`, `{{vars.*}}`, `{{steps.<id>.result}}`.
**Reason.** Цепочка Canvas → Definition → Runtime становится естественной; UI — визуальный редактор DSL (`backend_architecture_v1.md` §12–§13).
**Consequences.** Нужны валидатор/нормализатор документа; схема входа команд (`TOOL_FIELD_SCHEMA`) питает формы UI; ограничение — последовательные шаги, без параллелизма и композиции.

## D7. Tool Type ≠ Tool Instance

**Context.** У агента может быть несколько ботов/ключей одного типа; credentials привязаны к подключению.
**Alternatives.** Один «плагин» на тип с глобальными credentials.
**Decision.** Type (каталог: команды, события, configSchema, credentialPolicy) и Instance (per-agent: id, enabled, credentialId, config). Recipe ссылается на instance id; ссылка на type допустима при единственном включённом инстансе.
**Reason.** TOOLS_SDK §39 / alignment #14: контракт плагина отдельно от конкретного подключения агента к миру.
**Consequences.** Ошибки `ambiguous_tool_reference`, `disabled_tool_instance`; `credentialPolicy: unique_per_instance` для Telegram (валидация `duplicate_credential`).

## D8. Event — факт; completion-событие `action.<id>.completed`

**Context.** Нужен единый способ реагировать на результат операции в FSM и отличать команды от фактов.
**Alternatives.** `parse_request.completed` без префикса; generic `action.completed` для FSM; прямой вызов FSM из Tool.
**Decision.** Канон `action.<action_id>.completed` для FSM (RUNTIME §14), generic — только observability; имена событий `<domain>.<entity>.<past_verb>`; Tool не вызывает FSM (`alignment`: «Action completion trigger», «System vs FSM action events»).
**Reason.** Развязать Tools и Skills; единообразие guard-логики по `result.*` (EVENT_SPEC §2, agent_architecture §8, §12).
**Consequences.** Нарушается rewrite’ом диспетчера (D13) — признано долгом (`INTERACTION_NOTES_ARCHITECTURE_REVIEW.md` §15 R10.3).

## D9. LLM — Tool; не выбирает Action в FSM

**Context.** Где место LLM-решений.
**Alternatives.** LLM как «мозг», выбирающий следующий Action; LLM внутри recipe.
**Decision.** LLM — Tool (`llm`, `polza_ai_llm`) в рецепте; FSM выбирает action id по event/guard (alignment #5–#6).
**Reason.** Детерминизм процесса; runtime не зависит от провайдера (`backend_architecture_v1.md` §22).
**Consequences.** Структурированные выходы LLM (`parse_request`, `run_structured`) → `result.*` → guard; смена провайдера — смена инстанса, не Action.

## D10. Иммутабельные публикации + пин версии на run

**Context.** Запущенный процесс не должен внезапно исполняться по новой FSM.
**Alternatives.** Всегда latest; версии Skill внутри документа.
**Decision.** Публикация агента — неизменяемый снимок с SemVer patch-bump; run хранит `publication_version` и возобновляется по ней (`runtime_factory`, worker `_pinned_version_for_event`).
**Reason.** RUNTIME §4 / `backend_architecture_v1.md` §15.
**Consequences.** Версии Skill/Action внутри документа декоративны; живой агент видит новые рецепты только после republish (план Interaction фаза 5).

## D11. Разговор ≠ Skill Run

**Context.** Ждущий чат-скилл «съедал» клики по кнопкам с тем же `conversation_id`; два бота вместо коллеги (`INTERACTION_FUNDAMENTAL_PROBLEM.md`).
**Alternatives.** Один скилл на всё; `conversation_id` как владелец waiting-run; явный `skillId` на каждом событии.
**Decision.** Resume ждущего run только если его текущее состояние объявляет переход на `event.type`; 1 разговор → 0..N run; no-match ≠ error.
**Reason.** INTERACTION R0, R4.2, R5.1; errata RUNTIME §15 (план фаза 0–1).
**Consequences.** Q1/Q3 приёмки — «да»; потребовался диспетчер (D13), чтобы фраза находила работу.

## D12. Lock `conv-skill:{conversation}:{skill}`

**Context.** Полный lock разговора сериализовал чат и разбор; lock по `skill_run_id` форкал второй `razgovor`, пока первый в THINKING.
**Alternatives.** `conversation_id`; `skill_run_id`; без lock.
**Decision.** Ключ — разговор + скилл, когда оба известны; иначе run / entity / event (`runtime/event_lock.py`).
**Reason.** Докстринг `event_lock_key` и RUNTIME §18/§22.
**Consequences.** Два события одного скилла на нити — по очереди; разные скиллы — параллельно.

## D13. Диспетчер — таблица правил перед FSM

**Context.** Фраза «разбери» и кнопка «Разобрать» должны быть одной семьёй работ; «да» должно закрывать ожидание.
**Alternatives.** NLU/LLM-классификатор; логика внутри разговорного скилла; только `skillId` от клиента.
**Decision.** `classify_act` v1: тип события + intent + фокус + ключевые слова → класс; без LLM (план фаза 4).
**Reason.** INTERACTION §7, §15: выбор работы — классификация акта, не понимание текста; не делать разговорный скилл владельцем сессии.
**Consequences.** Работает при наличии фокуса/сущностей; rewrite типа события — признанный долг; `amend` = cancel+start.

## D14. Стол живёт во внешнем веб-клиенте

**Context.** Где правда дела (карточки, количества).
**Alternatives.** Канбан внутри runtime; копия бизнес-полей в `vars`.
**Decision.** Runtime читает snapshot (`web_client.get_snapshot`) и шлёт патчи (`workspace_update`); не хранит бизнес-данные (R1.4, RUNTIME §2).
**Reason.** «Runtime не ERP» — явное требование спек.
**Consequences.** Контракт веб-клиента (`/eva/*`) обязателен; `refresh_desk_snapshot` перед актом; Q6 зависит от рецепта.

## D15. Маршрутизация по документу агента

**Context.** Карта `EVA_DEFAULT_SKILL_IDS` (slug=skill) в env связывала деплой с конкретными агентами.
**Alternatives.** Оставить env-карту; требовать `skillId` всегда.
**Decision.** Приоритет: explicit `skillId` → уникальный initial-match → `defaultSkillId` среди match → `defaultSkillId` → env (deprecated, с warning) (коммит 77c5d78 «Route inbound events from the agent document instead of env skill maps»).
**Reason.** Сообщение коммита и докстринг `resolve_skill_for_event`.
**Consequences.** `defaultSkillId` в документе и валидация `invalid_default_skill`; env остаётся как fallback.

## D16. Каталог Tools только на сервере

**Context.** Дублирование манифестов в TS и Python расходилось.
**Decision.** `BUILTIN_TOOLS` в backend; `GET /api/tools/catalog`; `builtinTools = []` во фронтенде (коммит b8d1562 «schema-driven command input catalogs»; cheatsheet «no manual TS duplicate»).
**Reason.** Явно в cheatsheet `.cursor/skills/eva-specs/tools.md`.
**Consequences.** Формы UI schema-driven; unit-тесты фронтенда должны подставлять каталог (2 теста этого не делают — REVIEW).

## D17. Секреты stage/prod — Infisical

**Context.** Деплой в общую Docker-сеть экосистемы; не класть секреты в `.env` на сервере.
**Decision.** Compose читает окружение, которое подставляет `infisical run`; шаблоны в `infisical/*/` (коммиты defce8a, cc85371 «Source stage and prod runtime config from Infisical only»).
**Reason.** README раздел «Production / Stage»; сообщения коммитов.
**Consequences.** Makefile-обвязка; расхождение путей и пустые phony-цели после merge (REVIEW).

## D18. Настройки без значений по умолчанию

**Context.** Тихие дефолты маскировали ошибки конфигурации.
**Decision.** `_require*` для всех переменных (коммит e4093bc «Require explicit env for backend settings instead of silent defaults»).
**Reason.** Сообщение коммита.
**Consequences.** Старт падает при любой недостающей переменной; `.env.example` и Infisical-шаблоны должны быть полными.

## D19. `create_all` + `ALTER IF NOT EXISTS` вместо Alembic-ревизий

**Context.** Схема менялась часто на раннем этапе.
**Decision.** `EVA_AUTO_MIGRATE` → `Base.metadata.create_all` + ручные idempotent `ALTER TABLE`; Alembic — заглушка («optional — EVA_AUTO_MIGRATE uses create_all by default», `alembic/env.py`).
**Reason.** Причина решения не установлена по доступным материалам (кроме комментария об опциональности).
**Consequences.** Нет истории миграций; удаление/изменение колонок вручную; риск при расхождении схем между окружениями.

## D20. Без Session / Context Manager / Task Manager

**Context.** Соблазн ввести универсальный контейнер контекста.
**Decision.** Не вводить; ответственность распределена между Agent, Skill Run, Conversation, Tools (`agent_architecture_v1.md` §16–§18).
**Reason.** Такие сущности «легко превращаются в универсальный контейнер, знающий обо всём».
**Consequences.** Контекст — `vars` run + snapshot стола; при необходимости вернуть Session — только из требований runtime.

## D21. Planner вне scope v0.1

**Decision.** Отложить (`agent_architecture_v1.md` §23, §29; INTERACTION §15: диспетчер — не планировщик).
**Reason.** «Не нужно преждевременно фиксировать решение».
**Consequences.** Нет приоритизации очереди работ; остаётся открытым вопросом (research-questions A2).

## D22. Публикацию блокируют только `error`

**Decision.** `publish` отклоняет при `errors > 0`; warnings/info не блокируют (`AgentService.publish`).
**Reason.** Причина не зафиксирована; Inference — тупики и неиспользуемые Actions допустимы в черновой итерации.
**Consequences.** Можно опубликовать Skill с dead-end состояниями — run зависнет в `waiting`.

## D23. Архивация агента; отмена активных run

**Decision.** `archived_at` вместо удаления; при архивации все `running/waiting` run → `cancelled`; запрет редактирования/publish/новых run (409) (`AGENT_ARCHIVING_PLAN.md`, коммит 10e2c84).
**Reason.** План архивирования: сохранить историю и публикации, убрать агента из операционного контура.
**Consequences.** Cockpit фильтрует архивных; ingress отвечает 409; unarchive возвращает агента без восстановления отменённых run.
