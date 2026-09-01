from __future__ import annotations

from definition.catalog.manifests.stubs import (
    CATALOG_TOOL_MANIFEST,
    CONTEXT_TOOL_MANIFEST,
    CRM_TOOL_MANIFEST,
    FILES_TOOL_MANIFEST,
    MEMORY_TOOL_MANIFEST,
    SABY_TOOL_MANIFEST,
    WEB_SEARCH_TOOL_MANIFEST,
)
from tools.llm.manifest import LLM_TOOL_MANIFEST, POLZA_AI_LLM_TOOL_MANIFEST
from tools.telegram.manifest import TELEGRAM_TOOL_MANIFEST
from tools.text.manifest import TEXT_TOOL_MANIFEST
from tools.web_client.manifest import WEB_CLIENT_TOOL_MANIFEST

BUILTIN_TOOLS: list[dict] = [
    LLM_TOOL_MANIFEST,
    POLZA_AI_LLM_TOOL_MANIFEST,
    MEMORY_TOOL_MANIFEST,
    CONTEXT_TOOL_MANIFEST,
    TEXT_TOOL_MANIFEST,
    WEB_CLIENT_TOOL_MANIFEST,
    TELEGRAM_TOOL_MANIFEST,
    CRM_TOOL_MANIFEST,
    CATALOG_TOOL_MANIFEST,
    WEB_SEARCH_TOOL_MANIFEST,
    FILES_TOOL_MANIFEST,
    SABY_TOOL_MANIFEST,
]


def get_tool_definition(tool_id: str) -> dict | None:
    return next((tool for tool in BUILTIN_TOOLS if tool["id"] == tool_id), None)


def get_command_definition(tool_id: str, command_id: str) -> dict | None:
    tool = get_tool_definition(tool_id)
    if not tool:
        return None
    return next((cmd for cmd in tool.get("commands", []) if cmd.get("id") == command_id), None)


def get_command_input_schema(tool_id: str, command_id: str) -> list[dict]:
    command = get_command_definition(tool_id, command_id)
    if not command:
        return []
    schema = command.get("inputSchema")
    return list(schema) if isinstance(schema, list) else []


def get_command_output_schema(tool_id: str, command_id: str) -> list[dict]:
    command = get_command_definition(tool_id, command_id)
    if not command:
        return []
    schema = command.get("outputSchema")
    return list(schema) if isinstance(schema, list) else []


def iter_all_commands() -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    for tool in BUILTIN_TOOLS:
        tool_id = str(tool.get("id") or "")
        for command in tool.get("commands", []):
            if isinstance(command, dict) and command.get("id"):
                items.append((tool_id, command))
    return items
