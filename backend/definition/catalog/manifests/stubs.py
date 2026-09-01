from __future__ import annotations

from definition.catalog.field_defs import field

MEMORY_TOOL_MANIFEST: dict = {
    "id": "memory",
    "name": "Memory",
    "description": "Поиск по опыту и заметкам агента.",
    "commands": [
        {
            "id": "search",
            "description": "Семантический / ключевой поиск",
            "inputSchema": [
                field("query", type="template", required=True, label="Query"),
                field("filters", type="json", label="Filters (JSON)"),
            ],
            "outputSchema": [field("hits", type="json", scope="call")],
        },
    ],
    "events": [],
    "states": [],
}

CONTEXT_TOOL_MANIFEST: dict = {
    "id": "context",
    "name": "Context",
    "description": "Сборка порции мира на один шаг.",
    "commands": [
        {
            "id": "build",
            "description": "Собрать контекст по recipe",
            "inputSchema": [
                field("recipe_id", required=True, label="Recipe ID"),
                field("entity_refs", type="json", label="Entity refs"),
                field("session_id", type="template", label="Session ID"),
            ],
            "outputSchema": [
                field("context_bundle_id", type="string", scope="call"),
                field("slices", type="json", scope="call"),
            ],
        },
    ],
    "events": [],
    "states": [],
}

CRM_TOOL_MANIFEST: dict = {
    "id": "crm",
    "name": "CRM",
    "description": "Заявки и сущности в рабочей системе.",
    "commands": [
        {
            "id": "get",
            "description": "Прочитать сущность",
            "inputSchema": [
                field("entity_type", required=True, label="Entity type"),
                field("id", required=True, label="ID"),
            ],
            "outputSchema": [field("entity", type="json", scope="call")],
        },
        {
            "id": "update",
            "description": "Обновить сущность",
            "inputSchema": [
                field("entity_type", required=True, label="Entity type"),
                field("id", required=True, label="ID"),
                field("patch", type="json", required=True, label="Patch (JSON)"),
            ],
            "outputSchema": [field("entity", type="json", scope="call")],
        },
    ],
    "events": [
        {"id": "crm.request.created", "description": "Создана заявка"},
        {"id": "crm.request.updated", "description": "Обновлена заявка"},
    ],
    "states": [],
}

CATALOG_TOOL_MANIFEST: dict = {
    "id": "catalog",
    "name": "Catalog",
    "description": "Справочник ТМЦ и альтернатив.",
    "commands": [
        {
            "id": "search_tmc",
            "description": "Поиск позиций ТМЦ",
            "inputSchema": [
                field("query", type="template", required=True, label="Query"),
                field("filters", type="json", label="Filters"),
                field("limit", type="integer", default=20),
            ],
            "outputSchema": [field("items", type="json", scope="call")],
        },
        {
            "id": "search",
            "description": "Общий поиск по каталогу",
            "inputSchema": [
                field("query", type="template", required=True, label="Query"),
                field("limit", type="integer", default=20),
            ],
            "outputSchema": [field("items", type="json", scope="call")],
        },
    ],
    "events": [],
    "states": [],
}

WEB_SEARCH_TOOL_MANIFEST: dict = {
    "id": "web_search",
    "name": "Web Search",
    "description": "Поиск во внешнем вебе.",
    "commands": [
        {
            "id": "search",
            "description": "Веб-поиск",
            "inputSchema": [
                field("query", type="template", required=True, label="Query"),
                field("limit", type="integer", default=10),
            ],
            "outputSchema": [field("results", type="json", scope="call")],
        },
    ],
    "events": [],
    "states": [],
}

FILES_TOOL_MANIFEST: dict = {
    "id": "files",
    "name": "Files",
    "description": "Чтение и запись файлов.",
    "commands": [
        {
            "id": "read",
            "description": "Прочитать файл",
            "inputSchema": [
                field("path", required=True, label="Path"),
            ],
            "outputSchema": [field("content", type="text", scope="call")],
        },
        {
            "id": "write",
            "description": "Записать файл",
            "inputSchema": [
                field("path", required=True, label="Path"),
                field("content", type="text", required=True, label="Content"),
            ],
            "outputSchema": [field("ok", type="boolean", scope="call")],
        },
    ],
    "events": [],
    "states": [],
}

SABY_TOOL_MANIFEST: dict = {
    "id": "saby",
    "name": "Saby",
    "description": "Интеграция со СБИС / документооборотом.",
    "commands": [
        {
            "id": "send_document",
            "description": "Отправить документ",
            "inputSchema": [
                field("file_id", required=True, label="File ID"),
                field("counterparty_id", label="Counterparty ID"),
            ],
            "outputSchema": [field("delivery_id", type="string", scope="call")],
        },
        {
            "id": "get_status",
            "description": "Статус документа",
            "inputSchema": [
                field("document_id", required=True, label="Document ID"),
            ],
            "outputSchema": [field("status", type="string", scope="call")],
        },
    ],
    "events": [{"id": "saby.document.updated", "description": "Обновлён статус документа"}],
    "states": [],
}
