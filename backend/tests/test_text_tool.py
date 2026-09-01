from __future__ import annotations

import pytest

from runtime.definition_loader import build_tool_registry
from tools.text import TextTool
from tools.text.validators import MAX_TEXT_LENGTH


@pytest.fixture
def tool() -> TextTool:
    return TextTool()


def test_trim_both(tool: TextTool):
    result = tool.cmd_trim({"text": "  hello  "}, {})
    assert result.ok is True
    assert result.data["text"] == "hello"


def test_trim_left_and_right(tool: TextTool):
    left = tool.cmd_trim({"text": "  hello", "side": "left"}, {})
    right = tool.cmd_trim({"text": "hello  ", "side": "right"}, {})
    assert left.data["text"] == "hello"
    assert right.data["text"] == "hello"


def test_trim_custom_chars(tool: TextTool):
    result = tool.cmd_trim({"text": "...hello...", "chars": ".", "side": "both"}, {})
    assert result.data["text"] == "hello"


def test_normalize_collapse_and_case(tool: TextTool):
    result = tool.cmd_normalize(
        {
            "text": "  Hello   World  ",
            "collapse_whitespace": True,
            "case": "lower",
        },
        {},
    )
    assert result.data["text"] == "hello world"


def test_normalize_strip_empty_lines(tool: TextTool):
    result = tool.cmd_normalize(
        {
            "text": "line1\n\n  \nline2",
            "strip_empty_lines": True,
        },
        {},
    )
    assert result.data["text"] == "line1\nline2"


def test_truncate_with_suffix(tool: TextTool):
    result = tool.cmd_truncate({"text": "hello world", "max_length": 8, "suffix": "…"}, {})
    assert result.ok is True
    assert result.data["truncated"] is True
    assert result.data["text"] == "hello w…"
    assert result.data["original_length"] == 11


def test_truncate_word_boundary(tool: TextTool):
    result = tool.cmd_truncate(
        {"text": "hello beautiful world", "max_length": 12, "suffix": "…", "word_boundary": True},
        {},
    )
    assert result.data["text"] == "hello…"


def test_match_with_groups(tool: TextTool):
    result = tool.cmd_match({"text": "Invoice № 42", "pattern": r"№\s*(\d+)"}, {})
    assert result.data["matched"] is True
    assert result.data["match"] == "№ 42"
    assert result.data["groups"] == ["42"]


def test_match_named_groups(tool: TextTool):
    result = tool.cmd_match(
        {"text": "Invoice № 42", "pattern": r"№\s*(?P<num>\d+)"},
        {},
    )
    assert result.data["named_groups"] == {"num": "42"}


def test_match_not_found(tool: TextTool):
    result = tool.cmd_match({"text": "no numbers", "pattern": r"\d+"}, {})
    assert result.data["matched"] is False
    assert result.data["match"] is None


def test_extract_group(tool: TextTool):
    result = tool.cmd_extract(
        {"text": "Invoice № 42", "pattern": r"№\s*(\d+)", "group": 1},
        {},
    )
    assert result.data["found"] is True
    assert result.data["text"] == "42"


def test_extract_default(tool: TextTool):
    result = tool.cmd_extract(
        {"text": "no invoice", "pattern": r"№\s*(\d+)", "group": 1, "default": "n/a"},
        {},
    )
    assert result.data["found"] is False
    assert result.data["text"] == "n/a"


def test_find_all_with_limit(tool: TextTool):
    result = tool.cmd_find_all({"text": "a1 b2 c3", "pattern": r"\d", "limit": 2}, {})
    assert result.data["matches"] == ["1", "2"]
    assert result.data["count"] == 2


def test_contains_literal_and_regex(tool: TextTool):
    literal = tool.cmd_contains({"text": "Hello", "needle": "ell", "case_sensitive": False}, {})
    regex = tool.cmd_contains({"text": "Hello", "needle": r"^H", "regex": True}, {})
    assert literal.data["matched"] is True
    assert regex.data["matched"] is True


def test_replace_literal_and_regex(tool: TextTool):
    literal = tool.cmd_replace({"text": "foo bar foo", "pattern": "foo", "replacement": "baz"}, {})
    regex = tool.cmd_replace(
        {"text": "foo123 bar", "pattern": r"\d+", "replacement": "X", "regex": True},
        {},
    )
    assert literal.data["text"] == "baz bar baz"
    assert literal.data["replacements"] == 2
    assert regex.data["text"] == "fooX bar"


def test_remove_lines(tool: TextTool):
    text = "keep\n--\nОтправлено из Telegram\nkeep2"
    result = tool.cmd_remove_lines({"text": text, "pattern": r"^--$|^Отправлено"}, {})
    assert "Отправлено" not in result.data["text"]
    assert "keep" in result.data["text"]
    assert result.data["removed_count"] == 2


def test_remove_lines_invert(tool: TextTool):
    text = "keep\nERROR: bad\nkeep2"
    result = tool.cmd_remove_lines({"text": text, "pattern": r"^ERROR:", "invert": True}, {})
    assert result.data["text"].strip() == "ERROR: bad"


def test_split_and_join_roundtrip(tool: TextTool):
    split = tool.cmd_split({"text": "a\nb\nc", "separator": "\n", "trim_parts": True}, {})
    joined = tool.cmd_join({"parts": split.data["parts"], "separator": "|"}, {})
    assert split.data["parts"] == ["a", "b", "c"]
    assert joined.data["text"] == "a|b|c"


def test_split_skip_empty(tool: TextTool):
    result = tool.cmd_split({"text": "a,,b", "separator": ",", "skip_empty": True}, {})
    assert result.data["parts"] == ["a", "b"]


def test_invalid_regex(tool: TextTool):
    result = tool.cmd_match({"text": "x", "pattern": "("}, {})
    assert result.ok is False
    assert "invalid_pattern" in (result.error or "")


def test_missing_text(tool: TextTool):
    result = tool.cmd_trim({}, {})
    assert result.ok is False
    assert "required" in (result.error or "")


def test_text_too_long(tool: TextTool):
    result = tool.cmd_trim({"text": "x" * (MAX_TEXT_LENGTH + 1)}, {})
    assert result.ok is False
    assert "maximum length" in (result.error or "")


def test_join_requires_parts(tool: TextTool):
    result = tool.cmd_join({}, {})
    assert result.ok is False
    assert "parts" in (result.error or "")


def test_definition_loader_wires_text_tool():
    agent_body = {
        "slug": "demo",
        "tools": [{"id": "text-main", "toolId": "text", "enabled": True}],
    }
    registry = build_tool_registry(agent_body, agent_id="agent-1", session=None)
    tool = registry.require("text-main")
    assert tool.tool_type == "text"
    result = tool.cmd_trim({"text": "  ok  "}, {})
    assert result.ok is True
    assert result.data["text"] == "ok"
