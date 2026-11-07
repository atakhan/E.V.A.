from __future__ import annotations

from definition.catalog.field_defs import field

PULSE_TOOL_ID = "pulse"

PULSE_TOOL_MANIFEST: dict = {
    "id": PULSE_TOOL_ID,
    "name": "Пульс",
    "description": (
        "Самоощущение агента: кто я сейчас и какие коннекторы доступны "
        "(каналы/адреса, память, навыки, инструменты) со статусами."
    ),
    "world": False,
    "commands": [
        {
            "id": "self",
            "description": "Данные о себе — кто агент и в каком состоянии нить/жизнь",
            "inputSchema": [
                field("note", type="template", label="Заметка (необязательно)"),
            ],
            "outputSchema": [
                field("slug", type="string", scope="call"),
                field("name", type="string", scope="call"),
                field("kind", type="string", scope="call"),
                field("description", type="string", scope="call"),
                field("alive", type="boolean", scope="call"),
                field("life_skill", type="boolean", scope="call"),
                field("skill_run_id", type="string", scope="call"),
                field("self", type="json", scope="call"),
            ],
        },
        {
            "id": "connectors",
            "description": (
                "Проверить коннекторы: каналы и адреса, память, навыки, инструменты — "
                "что есть и какие статусы"
            ),
            "inputSchema": [
                field("note", type="template", label="Заметка (необязательно)"),
            ],
            "outputSchema": [
                field("channels", type="json", scope="call"),
                field("tools", type="json", scope="call"),
                field("skills", type="json", scope="call"),
                field("memory", type="json", scope="call"),
                field("summary", type="json", scope="call"),
            ],
        },
    ],
    "events": [],
    "states": [],
    "configSchema": [],
}
