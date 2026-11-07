from __future__ import annotations

from definition.catalog.field_defs import field

# Жизнь = глобальный FSM агента; этот плагин — машина, которая его исполняет.
# См. docs/06-experiments/life-skill-and-runtime-plugin.md
RUNTIME_TOOL_MANIFEST: dict = {
    "id": "runtime",
    "name": "Runtime",
    "description": (
        "Машина исполнения: такт жизни, доставка событий, старт эпизодов (навыков). "
        "Навык «Жизнь» — глобальный FSM агента; рантайм его исполняет."
    ),
    "implemented": False,
    "world": False,
    "commands": [
        {
            "id": "pulse",
            "description": "Такт жизни / подтверждение, что агент ещё здесь",
            "inputSchema": [
                field("note", type="template", label="Заметка"),
            ],
            "outputSchema": [
                field("ok", type="boolean", scope="call"),
                field("at", type="string", scope="call"),
            ],
        },
        {
            "id": "deliver_event",
            "description": "Доставить событие в нить жизни или эпизода",
            "inputSchema": [
                field("event_type", type="template", required=True, label="Тип события"),
                field("payload", type="json", label="Payload"),
                field("run_id", type="template", label="Run ID"),
            ],
            "outputSchema": [
                field("delivered", type="boolean", scope="call"),
                field("event_id", type="string", scope="call"),
            ],
        },
        {
            "id": "start_skill",
            "description": "Начать эпизод — другой навык — из жизни",
            "inputSchema": [
                field("skill_id", type="template", required=True, label="Skill ID"),
                field("params", type="json", label="Параметры"),
            ],
            "outputSchema": [
                field("run_id", type="string", scope="call"),
                field("started", type="boolean", scope="call"),
            ],
        },
        {
            "id": "await",
            "description": "Ждать событие или таймер внутри жизни",
            "inputSchema": [
                field("event_type", type="template", label="Тип события"),
                field("timeout_ms", type="integer", label="Таймаут (мс)"),
            ],
            "outputSchema": [
                field("reason", type="string", scope="call"),
                field("event", type="json", scope="call"),
            ],
        },
        {
            "id": "set_focus",
            "description": "Сдвинуть зону внимания (связь с памятью)",
            "inputSchema": [
                field("target", type="template", required=True, label="Цель внимания"),
                field("reason", type="template", label="Причина"),
            ],
            "outputSchema": [
                field("ok", type="boolean", scope="call"),
            ],
        },
    ],
    "events": [
        {"id": "runtime.pulsed", "description": "Такт жизни выполнен"},
        {"id": "runtime.skill_started", "description": "Эпизод (навык) стартовал"},
        {"id": "runtime.skill_finished", "description": "Эпизод (навык) завершился"},
    ],
    "states": [],
    "configSchema": [],
}
