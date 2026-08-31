from __future__ import annotations

"""Mirror of frontend builtinTools.ts for validation and API catalog."""

BUILTIN_TOOLS: list[dict] = [
    {
        "id": "llm",
        "name": "LLM",
        "description": "Языковая модель: текст и структурированный вывод (локальный stub).",
        "commands": [
            {"id": "run", "description": "Свободный текстовый ответ"},
            {"id": "run_structured", "description": "Ответ по JSON-схеме"},
            {"id": "parse_request", "description": "Разбор входящего запроса (runtime stub)"},
        ],
        "events": [],
        "states": [],
    },
    {
        "id": "polza_ai_llm",
        "name": "PolzaAI_LLM",
        "description": "LLM через Polza.ai (OpenAI-совместимый API): API key, модель, баланс и логи.",
        "commands": [
            {"id": "run", "description": "Chat completion — свободный текстовый ответ"},
            {"id": "run_structured", "description": "Ответ по JSON-схеме / json_object"},
            {"id": "parse_request", "description": "Разбор входящего запроса через LLM"},
        ],
        "events": [],
        "states": ["configured", "unconfigured"],
        "credentialKind": "api_key",
        "credentialPolicy": "shared_allowed",
        "configSchema": [
            {
                "id": "model",
                "type": "string",
                "required": False,
                "default": "gpt-4o-mini",
                "scope": "instance",
                "ui": {"label": "Модель по умолчанию"},
            }
        ],
    },
    {
        "id": "memory",
        "name": "Memory",
        "description": "Поиск по опыту и заметкам агента.",
        "commands": [{"id": "search", "description": "Семантический / ключевой поиск"}],
        "events": [],
        "states": [],
    },
    {
        "id": "context",
        "name": "Context",
        "description": "Сборка порции мира на один шаг.",
        "commands": [{"id": "build", "description": "Собрать контекст по recipe"}],
        "events": [],
        "states": [],
    },
    {
        "id": "web_client",
        "name": "Web Client",
        "description": "Интеграция с бэкендом веб-приложения: ingress/outbound HTTP API.",
        "commands": [
            {"id": "send_message", "description": "Отправить сообщение в UI веб-приложения"},
            {"id": "get_snapshot", "description": "Получить контекст сессии из веб-приложения"},
        ],
        "events": [
            {"id": "channel.message.received", "description": "Сообщение от пользователя в веб-приложении"},
            {"id": "web.state.changed", "description": "Изменилось состояние UI"},
        ],
        "states": ["disconnected", "connected"],
        "credentialKind": "web_client",
        "credentialPolicy": "unique_per_instance",
        "configSchema": [
            {"id": "healthPath", "type": "string", "default": "/eva/health", "ui": {"label": "Health path"}},
            {"id": "sendMessagePath", "type": "string", "default": "/eva/messages", "ui": {"label": "Send message path"}},
            {"id": "getSnapshotPath", "type": "string", "default": "/eva/context", "ui": {"label": "Snapshot path"}},
            {
                "id": "authStyle",
                "type": "enum",
                "enum": ["bearer", "x-api-key"],
                "default": "bearer",
                "ui": {"label": "Auth style"},
            },
            {"id": "timeoutSec", "type": "integer", "default": 30, "ui": {"label": "Timeout (sec)"}},
        ],
    },
    {
        "id": "telegram",
        "name": "Telegram",
        "description": "Канал сообщений с людьми.",
        "commands": [{"id": "send_message", "description": "Отправить сообщение"}],
        "events": [{"id": "channel.message.received", "description": "Входящее сообщение"}],
        "states": ["connected", "disconnected"],
        "credentialKind": "telegram_bot",
        "credentialPolicy": "unique_per_instance",
        "configSchema": [
            {"id": "default_chat_id", "type": "string", "required": False, "ui": {"label": "Chat ID по умолчанию"}},
            {
                "id": "parse_mode",
                "type": "enum",
                "enum": ["", "HTML", "Markdown"],
                "default": "",
                "ui": {"label": "Parse mode"},
            },
        ],
    },
    {
        "id": "crm",
        "name": "CRM",
        "description": "Заявки и сущности в рабочей системе.",
        "commands": [
            {"id": "update", "description": "Обновить сущность"},
            {"id": "get", "description": "Прочитать сущность"},
        ],
        "events": [
            {"id": "crm.request.created", "description": "Создана заявка"},
            {"id": "crm.request.updated", "description": "Обновлена заявка"},
        ],
        "states": [],
    },
    {
        "id": "catalog",
        "name": "Catalog",
        "description": "Справочник ТМЦ и альтернатив.",
        "commands": [
            {"id": "search_tmc", "description": "Поиск позиций ТМЦ"},
            {"id": "search", "description": "Общий поиск по каталогу"},
        ],
        "events": [],
        "states": [],
    },
    {
        "id": "web_search",
        "name": "Web Search",
        "description": "Поиск во внешнем вебе.",
        "commands": [{"id": "search", "description": "Веб-поиск"}],
        "events": [],
        "states": [],
    },
    {
        "id": "files",
        "name": "Files",
        "description": "Чтение и запись файлов.",
        "commands": [
            {"id": "read", "description": "Прочитать файл"},
            {"id": "write", "description": "Записать файл"},
        ],
        "events": [],
        "states": [],
    },
    {
        "id": "saby",
        "name": "Saby",
        "description": "Интеграция со СБИС / документооборотом.",
        "commands": [
            {"id": "send_document", "description": "Отправить документ"},
            {"id": "get_status", "description": "Статус документа"},
        ],
        "events": [{"id": "saby.document.updated", "description": "Обновлён статус документа"}],
        "states": [],
    },
]


def get_tool_definition(tool_id: str) -> dict | None:
    return next((tool for tool in BUILTIN_TOOLS if tool["id"] == tool_id), None)
