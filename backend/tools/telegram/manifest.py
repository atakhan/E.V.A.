from __future__ import annotations

from definition.catalog.field_defs import config_field, field

TELEGRAM_TOOL_MANIFEST: dict = {
    "id": "telegram",
    "name": "Telegram",
    "description": "Канал сообщений с людьми.",
    "commands": [
        {
            "id": "send_message",
            "description": "Отправить сообщение",
            "inputSchema": [
                field("chat_id", type="template", label="Chat ID", placeholder="{{vars.conversation_id}}"),
                field("text", type="template", required=True, label="Текст", placeholder="{{vars.last_message}}"),
            ],
            "outputSchema": [
                field("sent", type="json", scope="call"),
            ],
        },
    ],
    "events": [{"id": "channel.message.received", "description": "Входящее сообщение"}],
    "states": ["connected", "disconnected"],
    "credentialKind": "telegram_bot",
    "credentialPolicy": "unique_per_instance",
    "configSchema": [
        config_field("default_chat_id", label="Chat ID по умолчанию"),
        config_field("parse_mode", type="enum", enum=["", "HTML", "Markdown"], default="", label="Parse mode"),
    ],
}
