import pytest

from app.config import get_settings
from definition.catalog.builtin_tools import BUILTIN_TOOLS, iter_all_commands
from definition.schemas.agent_api import ToolDefinitionApi
from definition.validation.validate_agent import validate_agent
from runtime.definition_loader import build_tool_registry
from tools.text.tool import TextTool


def test_catalog_commands_have_input_schema():
    missing = []
    for tool_id, command in iter_all_commands():
        schema = command.get("inputSchema")
        if not schema:
            missing.append(f"{tool_id}.{command['id']}")
    assert missing == [], f"commands without inputSchema: {missing}"


def test_text_manifest_matches_tool_commands():
    text_tool = next(item for item in BUILTIN_TOOLS if item["id"] == "text")
    manifest_commands = {item["id"] for item in text_tool["commands"]}
    assert manifest_commands == set(TextTool.commands)


def test_text_replace_schema_has_required_fields():
    text_tool = next(item for item in BUILTIN_TOOLS if item["id"] == "text")
    replace = next(item for item in text_tool["commands"] if item["id"] == "replace")
    field_ids = {item["id"] for item in replace["inputSchema"]}
    assert {"text", "pattern"}.issubset(field_ids)


@pytest.mark.parametrize("tool", BUILTIN_TOOLS, ids=lambda tool: tool["id"])
def test_implemented_flag_matches_runtime_factory(tool, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "polza_mode", "stub")
    monkeypatch.setattr(settings, "telegram_mode", "stub")
    instance_id = f"{tool['id']}-main"
    body = {"slug": "demo", "tools": [{"id": instance_id, "toolId": tool["id"], "enabled": True}]}

    registry = build_tool_registry(body, agent_id="agent-1", session=None)

    assert (registry.get(instance_id) is not None) == ToolDefinitionApi.model_validate(tool).implemented


def _agent_with_memory_instance(*, enabled: bool) -> dict:
    return {
        "slug": "demo",
        "skills": [],
        "actions": [],
        "tools": [{"id": "memory", "toolId": "memory", "name": "Memory", "enabled": enabled}],
    }


def test_enabled_unimplemented_tool_is_validation_error():
    report = validate_agent(_agent_with_memory_instance(enabled=True))
    issue = next(item for item in report["issues"] if item["code"] == "unimplemented_tool")
    assert issue["severity"] == "error"
    assert issue["href"] == "/agents/demo/tools"


def test_disabled_unimplemented_tool_is_allowed():
    report = validate_agent(_agent_with_memory_instance(enabled=False))
    assert not any(item["code"] == "unimplemented_tool" for item in report["issues"])
