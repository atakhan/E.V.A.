from definition.validation.validate_tool_command_input import validate_command_input_errors_only


def test_text_replace_requires_pattern():
    errors = validate_command_input_errors_only("text", "replace", {"text": "hello"})
    assert any("pattern" in item for item in errors)


def test_text_replace_ok():
    errors = validate_command_input_errors_only(
        "text",
        "replace",
        {"text": "hello", "pattern": "h"},
    )
    assert errors == []
