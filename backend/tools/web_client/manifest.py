from __future__ import annotations

from definition.catalog.field_defs import config_field, field

WEB_CLIENT_TOOL_MANIFEST: dict = {
    "id": "web_client",
    "name": "Web Client",
    "description": "Интеграция с бэкендом веб-приложения: ingress/outbound HTTP API.",
    "commands": [
        {
            "id": "send_message",
            "description": "Отправить сообщение в UI веб-приложения",
            "inputSchema": [
                field("session_id", type="template", label="Session ID", placeholder="{{vars.conversation_id}}"),
                field("text", type="template", required=True, label="Текст", placeholder="{{vars.last_message}}"),
                field("meta", type="json", label="Meta (JSON)"),
                field("workspace_update", type="json", label="Патч мира"),
                field("ui_proposal", type="json", label="Предложение UI"),
            ],
            "outputSchema": [
                field("sent", type="json", scope="call"),
                field("statusCode", type="integer", scope="call"),
            ],
        },
        {
            "id": "get_snapshot",
            "description": "Получить контекст сессии из веб-приложения",
            "inputSchema": [
                field("session_id", type="template", required=True, label="Session ID", placeholder="{{vars.conversation_id}}"),
            ],
            "outputSchema": [
                field("snapshot", type="json", scope="call"),
            ],
        },
    ],
    "events": [
        {"id": "channel.message.received", "description": "Сообщение от пользователя в веб-приложении"},
        {"id": "web.state.changed", "description": "Изменилось состояние UI"},
    ],
    "states": ["disconnected", "connected"],
    "credentialKind": "web_client",
    "credentialPolicy": "unique_per_instance",
    "configSchema": [
        config_field("healthPath", default="/eva/health", label="Health path"),
        config_field("sendMessagePath", default="/eva/messages", label="Send message path"),
        config_field("getSnapshotPath", default="/eva/context", label="Snapshot path"),
        config_field("authStyle", type="enum", enum=["bearer", "x-api-key"], default="bearer", label="Auth style"),
        config_field("timeoutSec", type="integer", default=30, label="Timeout (sec)"),
    ],
}
