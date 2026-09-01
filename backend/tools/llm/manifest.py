from __future__ import annotations

from definition.catalog.field_defs import config_field, field

_LLM_RUN = {
    "id": "run",
    "description": "Свободный текстовый ответ",
    "inputSchema": [
        field("prompt", type="template", label="Prompt", placeholder="{{vars.last_message}}"),
    ],
    "outputSchema": [field("text", type="string", scope="call")],
}

_LLM_STRUCTURED = {
    "id": "run_structured",
    "description": "Ответ по JSON-схеме",
    "inputSchema": [
        field("prompt", type="template", label="Prompt"),
        field("schema", type="json", label="Schema (JSON)"),
    ],
    "outputSchema": [
        field("structured", type="json", scope="call"),
        field("ok", type="boolean", scope="call"),
    ],
}

_LLM_PARSE = {
    "id": "parse_request",
    "description": "Разбор входящего запроса",
    "inputSchema": [
        field("text", type="template", required=True, label="Текст", placeholder="{{vars.last_message}}"),
        field("force_clarification", type="boolean", default=False),
    ],
    "outputSchema": [
        field("parsed", type="json", scope="call"),
        field("needs_clarification", type="boolean", scope="call"),
    ],
}

LLM_TOOL_MANIFEST: dict = {
    "id": "llm",
    "name": "LLM",
    "description": "Языковая модель: текст и структурированный вывод (локальный stub).",
    "commands": [_LLM_RUN, _LLM_STRUCTURED, _LLM_PARSE],
    "events": [],
    "states": [],
}

POLZA_AI_LLM_TOOL_MANIFEST: dict = {
    "id": "polza_ai_llm",
    "name": "PolzaAI_LLM",
    "description": "LLM через Polza.ai (OpenAI-совместимый API): API key, модель, баланс и логи.",
    "commands": [
        {
            "id": "run",
            "description": "Chat completion — свободный текстовый ответ",
            "inputSchema": [
                field(
                    "messages",
                    type="json",
                    label="Messages (JSON)",
                    placeholder='[{"role":"user","content":"{{vars.last_message}}"}]',
                ),
                field("model", type="string", label="Model", placeholder="gpt-4o-mini"),
                field("temperature", type="string", label="Temperature", placeholder="0.2"),
                field("prompt", type="template", label="Prompt (legacy)"),
            ],
            "outputSchema": [field("text", type="string", scope="call")],
        },
        {
            "id": "run_structured",
            "description": "Ответ по JSON-схеме / json_object",
            "inputSchema": [
                field("messages", type="json", label="Messages (JSON)"),
                field("schema", type="json", label="Schema (JSON)"),
                field("model", type="string", label="Model"),
                field("prompt", type="template", label="Prompt (legacy)"),
            ],
            "outputSchema": [
                field("structured", type="json", scope="call"),
                field("ok", type="boolean", scope="call"),
            ],
        },
        {
            "id": "parse_request",
            "description": "Разбор входящего запроса через LLM",
            "inputSchema": [
                field("text", type="template", required=True, label="Текст", placeholder="{{vars.last_message}}"),
                field("schema", type="json", label="Schema (JSON)"),
                field("force_clarification", type="boolean", default=False),
            ],
            "outputSchema": [
                field("parsed", type="json", scope="call"),
                field("needs_clarification", type="boolean", scope="call"),
            ],
        },
    ],
    "events": [],
    "states": ["configured", "unconfigured"],
    "credentialKind": "api_key",
    "credentialPolicy": "shared_allowed",
    "configSchema": [
        config_field("model", default="gpt-4o-mini", label="Модель по умолчанию"),
    ],
}
