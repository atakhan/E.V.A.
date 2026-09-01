from definition.catalog.builtin_tools import BUILTIN_TOOLS, iter_all_commands
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
