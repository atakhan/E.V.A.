from __future__ import annotations

from definition.catalog.field_defs import field

AGENTS_TOOL_MANIFEST: dict = {
    "id": "agents",
    "name": "Агенты",
    "description": (
        "Канал к другим агентам Евы. Адрес — slug агента. "
        "Кто с кем связан и в какую сторону — в манифесте взаимодействия (память агента)."
    ),
    "world": True,
    "commands": [
        {
            "id": "send_message",
            "description": "Передать дело другому агенту",
            "inputSchema": [
                field("agent", type="template", required=True, label="Агент", placeholder="rt-pochta"),
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
