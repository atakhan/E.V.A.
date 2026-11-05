from __future__ import annotations

from definition.catalog.field_defs import config_field, field

SSH_COMMANDS_TOOL_MANIFEST: dict = {
    "id": "ssh_commands",
    "name": "SSH Commands",
    "description": (
        "Библиотека SSH-команд агента. Навык вызывает действие, действие вызывает run "
        "с id команды из библиотеки этого подключения."
    ),
    "commands": [
        {
            "id": "run",
            "description": "Выполнить команду из библиотеки возможностей этого подключения",
            "inputSchema": [
                field(
                    "command_id",
                    type="template",
                    required=True,
                    label="Команда библиотеки",
                    placeholder="restart_nginx",
                ),
                field("stdin", type="template", label="stdin"),
            ],
            "outputSchema": [
                field("command_id", type="string", scope="call"),
                field("exit_code", type="integer", scope="call"),
                field("stdout", type="string", scope="call"),
                field("stderr", type="string", scope="call"),
                field("truncated", type="boolean", scope="call"),
            ],
        },
    ],
    "events": [],
    "states": [],
    "credentialKind": "ssh_private_key",
    "credentialPolicy": "shared_allowed",
    "configSchema": [
        config_field("host", label="Хост"),
        config_field("port", type="integer", default=22, label="Порт"),
        config_field("username", label="Пользователь"),
        config_field("timeoutSec", type="integer", default=30, label="Таймаут (сек)"),
        config_field("outputLimit", type="integer", default=8000, label="Лимит вывода"),
        config_field(
            "hostKeyPolicy",
            type="enum",
            enum=["accept-new", "yes"],
            default="accept-new",
            label="Host key",
        ),
    ],
}
