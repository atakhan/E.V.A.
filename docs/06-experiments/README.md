# Experiments — архитектурные эксперименты проекта

> E.V.A. — не симуляционный и не численный проект; экспериментов с параметрами и измерениями в нём нет. Но проект развивался через **архитектурные эксперименты**: гипотеза → реализация → честная приёмка → решение оставить или снять. Они восстановлены по git history, `docs_old/` (в т.ч. `archive/`) и коду. Формат — из инструкции по документированию; «Observed results» — только то, что подтверждается материалами; интерпретации отделены.

Воспроизводимость здесь означает: можно вернуться к коммиту/документу и проверить описанное состояние.

---

## E1. Behavior Graph как source of truth конструктора (снят)

```text
Experiment:   Конструктор Skills на «семантическом графе поведения» (wait / do / decide) с двумя проекциями —
              Story (нарратив для человека) и Logic (FSM) — и компиляцией в states[] при publish.
Hypothesis:   FSM — не источник смысла, а исполняемый артефакт; человеку удобнее думать историей
              («получить сообщение → понять → найти → предложить → отправить»), а машине — автоматом.
              Промежуточная семантическая модель позволит редактировать оба представления без потери смысла.
Purpose:      Снизить порог входа для непрограммистов; сохранить детерминированное исполнение.
Parameters:   Узлы графа wait/do/decide; версия графа GRAPH_VERSION и компилятора COMPILER_VERSION;
              артефакт execution.states + compiledAt; проверка эквивалентности FSM↔Graph.
Environment:  Коммит 4d2ae2a (2026-09-03) «Add a Behavior Graph constructor and compile FSM on publish».
              Спеки: docs_old/archive/BEHAVIOR_SPEC.md, NEW_CONSTRUCTOR_DESC.md.
Procedure:    1) Ввести BehaviorGraph в документ Skill (поля behavior, execution, storyViewport, logicViewport).
              2) Вкладки «История · Логика» в UI; компиляция compile_behavior → states[] на publish.
              3) lift_fsm_to_behavior для обратного подъёма существующих FSM; equivalence-проверка.
              4) Прожить с этим ~2 недели параллельно с работой над Interaction-слоем.
Observed results (Fact):
              • 2026-09-16, коммит 4dea5f0 «Remove the Behavior Graph constructor and keep FSM as the skill editor»,
                e8ffbea «Archive withdrawn Behavior Graph constructor specs».
              • SKILLS_CONSTRUCTOR.md: «Ранний эксперимент с Behavior Graph / вкладкой „История“ / компилятором
                на publish снят». Канон: states[] — единственный source of truth, publish as-is, без compile.
              • Код компилятора оставлен только для одноразового flatten старых черновиков
                (definition/behavior/materialize.py, frontend normalizeSkill); поля графа удаляются при сохранении.
              • Тесты компилятора сохранены (test_behavior_compile.py, behaviorCompile.test.ts).
Interpretation (Inference):
              Промежуточный слой между холстом и runtime создавал второй источник истины и шаг compile,
              расходящийся с принципом «что нарисовано — то исполняется». Явной записи о причинах снятия
              в материалах нет — см. 07-decisions D5: «Причина решения не установлена по доступным материалам»
              в части конкретных аргументов.
Limitations:  Не было формальной приёмки (нет метрик удобства); решение принято автором проекта.
```

---

## E2. Слой взаимодействия: фазы 0–5 (control plane) — частично успешен

```text
Experiment:   Сделать агента «коллегой за столом», не переписывая исполнение Skill Run: добавить слой между
              человеческим актом и FSM — pin по типу события, N работ на разговоре, контракт акта (фокус/жест),
              таблица-диспетчер, снимок стола и эффекты/присутствие.
Hypothesis:   Гладкость чат + кнопки достижима набором различений (разговор ≠ работа ≠ сущность ≠ фокус)
              и control plane поверх v0.1, без NLU и без «одного скилла на всё».
Purpose:      Закрыть 6 вопросов приёмки INTERACTION_SPEC §16.
Parameters:   Ключ блокировки (conv-skill vs conversation); правила диспетчера (regex по словоформам, intent, фокус);
              классы resume/amend/start/side_question/cancel/underspecified; поля акта actorId/focus/intent/entityIds.
Environment:  Коммиты b70ce4b (спека), 5eaa512 (review/office metaphor), 5b4f642 (2026-09-07, control plane).
              Документы: docs_old/INTERACTION_SPEC_v0.1.md, INTERACTION_IMPLEMENTATION_PLAN.md,
              INTERACTION_IMPLEMENTATION_NOTES.md, INTERACTION_NOTES_ARCHITECTURE_REVIEW.md (+ OFFICE/BUREAU/WORLD/GAP).
Procedure:    Фаза 1 — resume ждущего run только если current_state ждёт event.type; no-match ≠ error.
              Фаза 2 — N run на conversation_id; lock conv-skill:{conversation}:{skill}.
              Фаза 3 — ingress принимает actor/focus/intent/entityIds; focus → metadata; actor → user_id.
              Фаза 4 — classify_act перед _resolve_targets (таблица, без LLM).
              Фаза 5 — refresh_desk_snapshot в vars; send_message несёт workspace_update/ui_proposal/presence;
                       web.state.changed как факт мира.
              Проверка: tests/test_interaction_routing.py, test_dispatcher.py, test_web_act.py, test_phase1_4.py.
Observed results (Fact, матрица §14 review и код):
              Q1 разбор + вопрос мимоходом без срыва      — ДА (разные скиллы, разные lock)
              Q2 кнопка и фраза — одна семья работ         — ДА, если есть фокус/entity; иначе underspecified
              Q3 ждущий чат не крадёт клик                 — ДА (pin по event.type)
              Q4 уточнение на карточке и в чате, любой ответ закрывает — ЧАСТИЧНО («да» → review слишком широко;
                                                             «мешки» не resume; якоря на карточке нет)
              Q5 «сначала Север» меняет пакет              — ДА, если entity в фокусе; реализовано как cancel+start
              Q6 после ручной правки агент говорит новую цифру — ОТЛОЖЕНО (факт на проводе; речь зависит от рецепта)
              Итог: 2.5 / 6 безусловных «да». 27 unit-тестов четырёх interaction-файлов проходят
              (ещё 4 integration в test_phase1_4.py требуют Postgres/Redis).
Interpretation (авторская, из review §15–19):
              Слой верный, онтология частично ложная: rewrite event.type диспетчером нарушает «Event = факт»;
              amend = cancel+start теряет историю; R1.4 (runtime не ERP) и R10.1–2 (Skill↛Tool) — несущие, держатся.
Limitations:  Диспетчер — regex-таблица по русским/английским словоформам; акцептанс-вопросы оценены вручную,
              не e2e-тестами с реальным веб-клиентом; Telegram вне контракта акта.
```

---

## E3. Foreman happy path — воспроизводимый сценарий ядра

```text
Experiment:   Прогнать один реальный процесс (заявка прораба в Telegram) через ядро Event → FSM → Action → Tool
              в памяти процесса, без БД — проверка «маленького чистого runtime» (backend_architecture §27).
Hypothesis:   Процесс с уточнением и ожиданием человека выражается 8–10 классами без спец-сущностей снабжения.
Purpose:      Доказательство жизнеспособности модели до добавления persistence/шины.
Parameters:   Skill process_foreman_request: NEW → ANALYZING → (CLARIFYING → WAITING_FOR_FOREMAN) → READY;
              Actions parse_request (text.normalize → llm.parse_request), clarify (telegram.send_message);
              LLM-stub: needs_clarification = «гриб» в тексте; guard result.needs_clarification == true/false.
Environment:  backend/scenarios/foreman_request.py, foreman_agent_document.py; EventRouter (in-memory);
              ToolRegistry.with_stubs(). Запуск: POST /api/runtime/demo или pytest tests/test_foreman_scenario.py.
Procedure:    scripted_events(): channel.message.received «нужны грибки…» → ожидается CLARIFYING/WAITING_FOR_FOREMAN
              и одно stub-сообщение; второе сообщение того же conversation_id → READY (completed).
Observed results (Fact): test_foreman_scenario.py проходит; demo возвращает history, tool_calls, telegram_sent.
Interpretation: Модель покрывает «уточнить и подождать»; это минимальная демонстрация, не нагрузка и не реальный LLM.
Limitations:  In-memory путь (EventRouter) отличается от production (RuntimeService): нет диспетчера, нет пина версий.
```

---

## E4. Три процесса снабжения через одну модель — не завершён

```text
Experiment:   agent_architecture_v1.md §30: выразить process_foreman_request, negotiate_supplier, process_invoice
              без «снабженческих» сущностей в ядре.
Status:       Выполнен 1 из 3 (foreman). Дополнительно реализованы razgovor (диалог) и process_supplier_request
              (жесты UI) — другой тип процессов, не из списка. negotiate_supplier и process_invoice отсутствуют.
Observed:     Fact — в коде/документах нет Skills с такими id.
Interpretation: Критерий универсальности ядра пока не подтверждён в объёме, заявленном архитектурой.
```

---

## Как добавлять записи

Новая запись — в этот файл или отдельным `E<N>-<slug>.md` рядом, по тому же шаблону. Обязательно: ссылка на коммит(ы) и на документ-основание; разделять «Observed results» (что видно в коде/тестах/документах) и «Interpretation».
