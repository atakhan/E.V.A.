# Критические заметки: внедрение слоя взаимодействия

> Живой файл. Не план и не канон. Сюда — сомнения, побочные эффекты, где фаза сделала меньше, чем кажется.  
> План: [`INTERACTION_IMPLEMENTATION_PLAN.md`](./INTERACTION_IMPLEMENTATION_PLAN.md).  
> Канон: [`INTERACTION_SPEC_v0.1.md`](./INTERACTION_SPEC_v0.1.md).  
> Синтез (архитектор): [`INTERACTION_NOTES_ARCHITECTURE_REVIEW.md`](./INTERACTION_NOTES_ARCHITECTURE_REVIEW.md).

Пишется **параллельно** с работой по плану, не после «когда всё готово».

---

## Как читать

Каждая запись: что сделали → что из этого следует → что план недоговорил или где мы срезали угол.

Сквозные напряжения (прокси, rewrite типа, lock vs кардинальность, seed ≠ publication) собраны в [`INTERACTION_NOTES_ARCHITECTURE_REVIEW.md`](./INTERACTION_NOTES_ARCHITECTURE_REVIEW.md). Новые записи лучше ссылаться на якоря оттуда (§7 rewrite, §8 lock, §9 publication), а не начинать манифест заново.

---

## 2026-09-06 — старт: фазы 0 и 1 в одном ходе

План просил не смешивать PR 0 (спеки) и PR 1 (pin) в одном коммите. Пользователь сказал выполнять план целиком и вести заметки рядом. **Спека и код фазы 1 идут вместе в этой сессии.** Риск, от которого план предостерегал: если pin в коде разъедется с формулировкой RUNTIME, опять два канона. Поэтому errata в RUNTIME/EVENT пишется теми же словами, что и условие в `waiting_runs_matching_event`.

---

## Фаза 0 — спеки

### Что сделано

Errata routing в RUNTIME §15 / §19–20 / §22; EVENT §10: `conversation_id` — голос, не владелец FSM; `user_id` = актёр; `focus` в metadata акта. INTERACTION §14: `skillId` — подсказка. Decision log уже был сведён раньше.

### Критика

1. **`actor_id` vs `user_id`.** INTERACTION пишет `actor_id`, envelope уже имеет `user_id`. Добавлять второе поле в correlation — дубль. В errata сказано: веб-контракт `actor_id` кладётся в `user_id`. Пока клиент этого не шлёт, R9.2 на бумаге.

2. **`focus` в metadata, не в correlation.** Правильно (эфемерно). Но ни ingress, ни `enqueue_channel_event` его не ждут — фаза 3. Спека опережает проводку; это сознательно, иначе фаза 1 снова чинит «баг» без нормы.

3. **Lock на `skill_run_id` записан в RUNTIME, код фазы 1 его не меняет.** Worker по-прежнему берёт `conversation_id` как ключ lock. Спека на шаг впереди кода. Иначе фаза 2 некуда будет целиться. **Нельзя читать RUNTIME §18 как описание текущего worker.**

4. **«Состояние явно ждёт event.type»** — грубый прокси «акт = ответ этой работе». Guard на переходе не проверяем на этапе pin (дорого и рано). Скилл с широким `channel.message.received` в IDLE по-прежнему сожрёт любое сообщение, включая «разбери». Фаза 1 чинит **кнопку vs чат по типу события**, не фразу vs кнопку. Приёмка §16 вопрос 2 после фазы 1 всё ещё нет — план это знал, легко забыть.

---

## Фаза 1 — pin и no-match (сделано)

### Что сделано

- `waiting_runs_matching_event` / `run_accepts_event` — resume только если current_state объявляет этот `event.type`.
- Worker больше не берёт «последний waiting по conversation» вслепую; без publication body **вообще не pin'ит** по сессии (безопаснее старого).
- `_resolve_targets` фильтрует waiting; иначе стартует скилл по initial-state.
- `_service_for_skill` без DB клонирует каталог из `publication_body` (иначе unit-тест не стартовал бы второй скилл).
- No-match: SkillRunner не кидает `RuntimeError`; `_route_single` не вливает payload в `vars`, если run не цель.
- InMemory store сканирует **все** waiting/running с этим `conversation_id` (кусок фазы 2). Без этого фильтр в тестах врал бы.
- Тесты: `backend/tests/test_interaction_routing.py`. 92 unit-теста зелёные.

### Критика после кода

1. **Приёмка вопроса 2 не сдвинулась.** «Разбери» в чате по-прежнему `channel.message.received` → razgovor. Мы научили кнопку не умирать в чате, не научили фразу стать кнопкой. Легко продать фазу 1 как «диспетчер». Это не он.

2. **Guard на pin не смотрим.** Скилл с переходом на `channel.message.received` в IDLE без guard сожрёт любое сообщение. Спека это допускает («guard при apply»). Для «да» vs «разбери» этого мало.

3. **Lock всё ещё `conversation_id`.** RUNTIME §18 уже врёт относительно worker. Два run на одной сессии не стартуют параллельно: parse ждёт, пока чат отпустит lock. Вопрос 1 «не срывает» — да как error; «одновременно» — нет.

4. **`GET /api/runtime/runs/by-conversation`** по-прежнему один run (`find_waiting_by_conversation` = latest). Cockpit будет врать, когда чат и разбор живы вместе.

5. **`_service_for_run(... ) or self`** — если клон каталога не удался, чужой run обрабатывается runner'ом не того скилла. No-match спасёт от error, не от путаницы. Редко, но дыра.

6. **Фильтр без `publication_body`** в `_resolve_targets` откатывается к старому «все waiting». HTTP/worker всегда с публикацией; голый EventRouter/RuntimeService без body снова опасен.

7. **Worker не покрыт тестом.** Unit-тесты бьют RuntimeService. Регрессия pin в `_matching_waiting_run` возможна молча, если кто-то вернёт `find_waiting_by_conversation`. Стоит тест на саму функцию worker'а (она чистая).

8. **Спека и код снова в одном ходе**, как план запрещал. Спасает то, что условие pin буквально одно и то же, что §15. Следующую фазу (lock) лучше не смешивать с диспетчером.

9. **Postgres `find_waiting_runs` включает `running`.** Чат в THINKING (ждёт `action.draft_reply.completed`) не матчит parse — хорошо. Но parse не начнётся, пока worker держит lock на сессию и пока чат не докрутит handle(). На практике «кнопка во время печати ответа» встанет в очередь, не упадёт.

### Что не делать дальше из эйфории

Не вшивать NLU в razgovor. Не трогать конструктор. Фаза 2 ниже закрыла lock и список run. Фаза 3: focus на проводе. Диспетчер — после этого.

---

## Фаза 2 — lock и N run (сделано)

### Что сделано

- `event_lock_key`: при известных `conversation_id` + `skill_id` ключ `conv-skill:{conversation}:{skill}` — и inbound, и targeted completion. Чат и разбор не делят lock; два чата сериализуются.
- Worker считает ключ в peek-сессии (`matching_waiting_run` / resolve / run.skill_id), затем `correlation_lock`, затем снова резолвит внутри lock.
- InMemory `by_conversation` — список id; `store_save_run` append. Postgres `find_waiting_runs` и раньше возвращал все active.
- `GET /api/runtime/runs/by-conversation` отдаёт `items[]` всех waiting/running; верхний `skillRunId` — первый (latest `updated_at`) ради совместимости.
- Слитый тест фазы 1 снова два теста. Добавлены: два waiting на одной нити, `matching_waiting_run` без body не pin'ит, lock keys.

### Критика после кода

1. **Это не lock на `skill_run_id`.** Чистый `run:` на inbound, пока первый чат ещё THINKING (state не ждёт `channel.message.received`), даёт второй `razgovor`. `conv-skill` — сознательный откат от формулировки RUNTIME «lock = run». Спека §18 теперь описывает фактический ключ; не читать «skill_run_id» в списке как единственный код.

2. **Два run одного скилла на нити сериализуются.** Два параллельных разбора на одном разговоре (две карточки) встанут в очередь worker'а. Вопрос 1 про чат vs разбор — закрыт. Параллельность *одного* класса работ — нет. Если понадобится, ключ должен стать `run:` или `entity:{request_id}` *после* того, как run уже есть, и отдельно сериализовать только «ещё нет run».

3. **Peek сессии до lock.** Ключ считается вне lock, обработка — внутри. Между peek и lock состав waiting может смениться. На практике skill_id с события стабилен (тип → скилл), TOCTOU скорее даст тот же `conv-skill`, не чужой. Если peek не нашёл skill (нет slug) — ключ `event:{id}`, два таких чата могут форкнуть. Это путь битого конверта.

4. **Singular `skillRunId` в API — ложь совместимости.** Клиент, который смотрит только верхнее поле, по-прежнему видит latest. Cockpit фронта этого эндпоинта не зовёт (список идёт через `GET /runs`). `find_waiting_by_conversation` жив и всё ещё `[0]`.

5. **Worker lock не покрыт интеграционным тестом** (два воркера, Redis lock). Юнит бьёт `event_lock_key` + `matching_waiting_run` + InMemory store. Регрессия «опять lock на conversation_id» в `_lock_key_for_event` возможна, если кто-то вернёт payload conversation как ключ. Стоит тест на саму `_lock_key_for_event` с фейковым store, когда появится время.

6. **`_service_for_run(... ) or self` не трогали.** Дыра фазы 1 жива.

7. **Фильтр без `publication_body` не трогали.** Голый RuntimeService без body снова pin'ит все waiting.

8. **Спека и код снова в одном ходе.** Условие lock теперь совпадает с §18. Следующую фазу (ingress focus) лучше не смешивать с диспетчером.

### Что не делать дальше из эйфории

Не вшивать NLU в razgovor. Не дробить lock до `run:` пока нет защиты от форка чата. Фаза 3 ниже закрыла провод акта. Диспетчер классов — фаза 4.

---

## Фаза 3 — контракт акта (сделано)

### Что сделано

- `normalize_web_act`: `actor_id` → `user_id` / `sender_id`; focus в camelCase в payload **и** `metadata.focus`; `entity_ids` + первый как `entity_id`; `intent` на payload.
- `enqueue_channel_event` нормализует до сборки Event и пишет correlation `user_id` / `entity_id` / `request_id` (validator Event не перезапускается при дописывании payload).
- `WebEventRequest`: верхние `actorId`, `focus`, `intent`, `entityIds`; snapshot сессии их помнит.
- ai_supplier: `forward_to_eva` всегда шлёт `actorId` (`ai-supplier:operator` по умолчанию); чат — focus стола; dispatch — intent/entityIds (с кнопки или из `request_id`).
- Кнопки UI: `deskFocus()` (вкладка + открытая карточка); parse → `intent: parse`, review → `intent: review`.
- Тесты: `tests/test_web_act.py`; run vars получают focus/intent.

### Критика после кода

1. **Вопрос 2 не сдвинулся.** Фокус на фразе «разбери это» теперь есть в payload, но событие всё ещё `channel.message.received` → razgovor. Кнопка по-прежнему другой `event.type` + `skillId`. Мы научили провод не терять объект, не научили фразу стать жестом.

2. **`actor_id` — константа.** Нет пользователя в ai_supplier. `ai-supplier:operator` закрывает поле, не R9.2 «кто нажал». Не делать вид, что аутентификация появилась.

3. **Focus чата грубый.** `view` = вкладка, `openEntityId` = модалка или аргумент кнопки. Топик Telegram торчит как `topicId` (лишний ключ). Нет selected-ряда карточек на канбане. «Это» без открытой карточки — пустой focus.

4. **Дубль payload + metadata.** Рецепты читают `payload`/`vars`, спека канонит `metadata.focus`. Держим оба, пока templates не умеют metadata. Риск разъехаться, если кто-то поправит только одно место.

5. **Ingress нормализует дважды** (web.py для snapshot, потом enqueue). Идемпотентно, но не красиво. Не выносить в middleware.

6. **`skillId` на кнопке остался.** План разрешал. Диспетчер фазы 4 должен уметь выбрать parse без него; пока подсказка всё ещё главный путь канбана.

7. **Backend dispatch без фронта** подставляет focus из `request_id`. Удобно для curl. Чуть больше магии, чем «клиент всегда шлёт акт».

8. **Telegram ingress не трогали.** `sender_id` как был. Фокус в телеге — не эта фаза.

9. **Браузерно не гоняли** в этом ходе (нет обязательного живого UI). Регресс кнопок/чата проверять на стенде: payload в Redis/логах worker должен содержать `focus` и `entity_ids`.

### Что не делать дальше из эйфории

Не вшивать NLU в razgovor. Не мапить фразу «разбери» на parse внутри чат-скилла. Фазы 4–5 ниже.

---

## Фаза 4 — диспетчер (сделано)

### Что сделано

- `classify_act` до `_resolve_targets`: жесты `ui.*` / `human.*` — start/resume работы; чат «разбери» при фокусе переписывается в `ui.request.parse_requested`; «стоп» cancel работы + чат; «сначала» при entity в фокусе — cancel+start; «да» — `human.request.reviewed`; вопрос («кто», `?`) — razgovor, работу не трогает.
- Worker peek применяет ту же классификацию до lock, чтобы «разбери» брало `conv-skill` разбора, не чата.
- Тесты: `tests/test_dispatcher.py`.

### Критика после кода

1. **Это таблица, не понимание.** «Разбери сомнительные по Северу» без выбранных карточек не сузит пакет. Deictic «это» без focus → underspecified (чат переспросит), не молчаливый parse.

2. **«Да» при любом живом process-run = review.** Если человек сказал «да» в смысле «да, а поставщик кто?» без `?` — сожрём как approve. Риск известный; вопрос с `?` или «кто» уходит в чат.

3. **Amend = cancel + start.** История старого run обрывается. Нет сужения очереди внутри того же FSM.

4. **Свободный ответ на уточнение («мешки») не resume**, пока work-скилл не ждёт `channel.message.received` в этом state. process_supplier_request в READY этого не ждёт. Вопрос 4 не полный.

5. **Двойной classify** (peek lock + `route_all`). Идемпотентно на переписанном event. Cancel применяется только во втором. Между peek и lock состав waiting может смениться.

6. **Не LLM и не конструктор.** Ключевые слова зашиты в `dispatcher.py`. Смена языка/синонимов — правка кода, не скилла.

### Что не делать дальше из эйфории

Не тащить классификатор в `razgovor`. Если понадобится «мешки» как ответ работе — пусть work-скилл в состоянии уточнения ждёт чат, диспетчер уже resume'ит такой wait.

---

## Фаза 5 — стол и эффекты (сделано, с дырами)

### Что сделано

- Перед handle: `refresh_desk_snapshot` → `vars._desk` / `_desk_text` + overlay quantity/unit/title с карточки.
- Seed: `draft_reply` зовёт `get_snapshot`; prompt требует цифры со стола. `parse_request` — snapshot, затем `workspace_update` первым классом.
- `send_message`: `workspace_update`, `ui_proposal`, автоматически `presence` живых run сессии.
- ai_supplier PATCH карточки → `web.state.changed` без принудительного `skillId`. Ingress пропускает unrouted `web.*`. Worker ack'ает факт без скилла.
- Чат UI: badges presence из snapshot.

### Критика после кода

1. **Опубликованный агент в DB не обновился.** Seed-рецепты меняются в репозитории. Пока не republish `supplier-agent`, LLM в проде не видит `{{vars._desk_text}}`. Runtime всё же кладёт `_desk` в vars — рецепт его не читает.

2. **Нет реплики сразу после ручной правки.** Факт уходит. Скилла на `web.state.changed` нет. Вопрос 6 «агент говорит новую цифру» = со *следующей* реплики, если рецепт читает стол.

3. **`ui.proposal` на проводе, UI почти не рисует.** Пишем в session `uiProposal`. Канбан не подсвечивает карточки. Контракт есть, жест на столе — нет.

4. **Presence только с исходящим `send_message`.** Cancel без последующего чата оставит старые badges. «Стоп» у нас follow-with-chat — ок. Тихий cancel через cockpit API — presence устареет.

5. **get_snapshot в рецепте может уронить action**, если web_client недоступен. Runtime inject отдельно; падение recipe — отдельный риск после republish.

6. **Два человека (R9.2) не решали.** actor по-прежнему константа.

7. **Браузерно не гоняли.** На стенде: «разбери это» с открытой карточкой должно стартовать parse; «кто по арматуре?» — нет; PATCH количества + следующий чат — новая цифра, если агент переопубликован.
