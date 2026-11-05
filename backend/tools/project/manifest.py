from __future__ import annotations

from definition.catalog.field_defs import field

PROJECT_TOOL_MANIFEST: dict = {
    "id": "project",
    "name": "Проект",
    "description": "Канал к другому проекту Евы. Коннектор — адрес проекта. Доставка сверяется с объявлением навыка.",
    "world": True,
    "commands": [
        {
            "id": "send_message",
            "description": "Передать дело другому агенту",
            "inputSchema": [
                field("project", type="template", label="Проект", placeholder="pochta-ofisa"),
                field("agent", type="template", label="Агент"),
                field("matter", type="template", required=True, label="Дело", placeholder="описание падения"),
                field("text", type="template", required=True, label="Текст"),
                field("conversation_id", type="template", label="Нить", placeholder="{{vars.conversation_id}}"),
                field("waits", type="boolean", label="Жду ответ"),
                field("reply", type="boolean", label="Это ответ"),
            ],
            "outputSchema": [
                field("delivered", type="boolean", scope="call"),
                field("reason", type="string", scope="call"),
                field("skill_id", type="string", scope="call"),
                field("conversation_id", type="string", scope="call"),
                field("reply_allowed", type="boolean", scope="call"),
            ],
        }
    ],
    "events": [
        {"id": "agent.message.received", "description": "Другой агент передал дело"},
        {"id": "agent.message.declined", "description": "Дело не принято"},
    ],
    "states": [],
    "configSchema": [],
}
