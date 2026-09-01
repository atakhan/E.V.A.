from __future__ import annotations

import re
import unicodedata
from typing import Any

from domain.events import ToolResult
from tools.base import BaseTool
from tools.text.regex_utils import compile_pattern, parse_flags
from tools.text.validators import (
    DEFAULT_FIND_ALL_LIMIT,
    clamp_limit,
    require_parts,
    require_text,
)


class TextTool(BaseTool):
    id = "text"
    commands = (
        "trim",
        "normalize",
        "truncate",
        "match",
        "extract",
        "find_all",
        "contains",
        "replace",
        "remove_lines",
        "split",
        "join",
    )

    def cmd_trim(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        chars = args.get("chars")
        side = str(args.get("side") or "both").lower()
        if chars is None:
            stripped = text.strip() if side == "both" else text.lstrip() if side == "left" else text.rstrip()
        else:
            strip_chars = str(chars)
            if side == "left":
                stripped = text.lstrip(strip_chars)
            elif side == "right":
                stripped = text.rstrip(strip_chars)
            else:
                stripped = text.strip(strip_chars)
        return ToolResult(ok=True, data={"text": stripped})

    def cmd_normalize(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        unicode_form = str(args.get("unicode_form") or "none").upper()
        if unicode_form in {"NFC", "NFKC"}:
            text = unicodedata.normalize(unicode_form, text)

        if args.get("collapse_whitespace"):
            text = re.sub(r"\s+", " ", text).strip()

        if args.get("strip_empty_lines"):
            lines = [line for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)

        case = str(args.get("case") or "none").lower()
        if case == "lower":
            text = text.lower()
        elif case == "upper":
            text = text.upper()

        return ToolResult(ok=True, data={"text": text})

    def cmd_truncate(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        try:
            max_length = int(args.get("max_length"))
        except (TypeError, ValueError):
            return ToolResult(ok=False, error="text.max_length is required and must be an integer")

        if max_length < 0:
            return ToolResult(ok=False, error="text.max_length must be non-negative")

        original_length = len(text)
        if original_length <= max_length:
            return ToolResult(
                ok=True,
                data={"text": text, "truncated": False, "original_length": original_length},
            )

        suffix = str(args.get("suffix") if args.get("suffix") is not None else "…")
        word_boundary = bool(args.get("word_boundary"))

        if word_boundary and max_length > len(suffix):
            cut_at = max_length - len(suffix)
            candidate = text[:cut_at]
            last_space = candidate.rfind(" ")
            if last_space > 0:
                candidate = candidate[:last_space]
            truncated_text = candidate.rstrip() + suffix
        else:
            reserve = len(suffix)
            cut_at = max(0, max_length - reserve)
            truncated_text = text[:cut_at] + suffix

        return ToolResult(
            ok=True,
            data={
                "text": truncated_text,
                "truncated": True,
                "original_length": original_length,
            },
        )

    def cmd_match(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        pattern = args.get("pattern")
        if not pattern:
            return ToolResult(ok=False, error="text.pattern is required")

        compiled = compile_pattern(str(pattern), args.get("flags"))
        if isinstance(compiled, ToolResult):
            return compiled

        match = compiled.search(text)
        if not match:
            return ToolResult(
                ok=True,
                data={"matched": False, "match": None, "groups": [], "named_groups": {}},
            )

        return ToolResult(
            ok=True,
            data={
                "matched": True,
                "match": match.group(0),
                "groups": list(match.groups()),
                "named_groups": match.groupdict(),
            },
        )

    def cmd_extract(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        pattern = args.get("pattern")
        if not pattern:
            return ToolResult(ok=False, error="text.pattern is required")

        compiled = compile_pattern(str(pattern), args.get("flags"))
        if isinstance(compiled, ToolResult):
            return compiled

        match = compiled.search(text)
        if not match:
            default = args.get("default")
            return ToolResult(ok=True, data={"text": default, "found": False})

        group = args.get("group", 0)
        try:
            if isinstance(group, str) and group.isdigit():
                group = int(group)
            extracted = match.group(group)
        except (IndexError, KeyError):
            default = args.get("default")
            return ToolResult(ok=True, data={"text": default, "found": False})

        return ToolResult(ok=True, data={"text": extracted, "found": True})

    def cmd_find_all(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        pattern = args.get("pattern")
        if not pattern:
            return ToolResult(ok=False, error="text.pattern is required")

        compiled = compile_pattern(str(pattern), args.get("flags"))
        if isinstance(compiled, ToolResult):
            return compiled

        limit = clamp_limit(args.get("limit"), default=DEFAULT_FIND_ALL_LIMIT, maximum=10_000)
        matches = compiled.findall(text)
        if matches and isinstance(matches[0], tuple):
            matches = ["".join(item) for item in matches]
        else:
            matches = [str(item) for item in matches]

        limited = matches[:limit]
        return ToolResult(ok=True, data={"matches": limited, "count": len(limited)})

    def cmd_contains(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        needle = args.get("needle")
        if needle is None:
            return ToolResult(ok=False, error="text.needle is required")

        use_regex = bool(args.get("regex"))
        if use_regex:
            compiled = compile_pattern(str(needle), args.get("flags"))
            if isinstance(compiled, ToolResult):
                return compiled
            matched = compiled.search(text) is not None
        else:
            needle_text = str(needle)
            case_sensitive = args.get("case_sensitive", True)
            if case_sensitive:
                matched = needle_text in text
            else:
                matched = needle_text.lower() in text.lower()

        return ToolResult(ok=True, data={"matched": matched})

    def cmd_replace(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        pattern = args.get("pattern")
        if pattern is None:
            return ToolResult(ok=False, error="text.pattern is required")

        replacement = str(args.get("replacement", ""))
        use_regex = bool(args.get("regex"))
        count = int(args.get("count") or 0)

        if use_regex:
            compiled = compile_pattern(str(pattern), args.get("flags"))
            if isinstance(compiled, ToolResult):
                return compiled
            result_text, replacements = compiled.subn(replacement, text, count=count)
        else:
            pattern_text = str(pattern)
            if count == 0:
                replacements = text.count(pattern_text)
                result_text = text.replace(pattern_text, replacement)
            else:
                result_text = text.replace(pattern_text, replacement, count)
                replacements = min(count, text.count(pattern_text))

        return ToolResult(ok=True, data={"text": result_text, "replacements": replacements})

    def cmd_remove_lines(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        pattern = args.get("pattern")
        if not pattern:
            return ToolResult(ok=False, error="text.pattern is required")

        flags = args.get("flags", "m")
        compiled = compile_pattern(str(pattern), flags)
        if isinstance(compiled, ToolResult):
            return compiled

        invert = bool(args.get("invert"))
        kept: list[str] = []
        removed_count = 0
        for line in text.splitlines(keepends=True):
            line_body = line.rstrip("\r\n")
            matches = compiled.search(line_body) is not None
            should_remove = matches if not invert else not matches
            if should_remove:
                removed_count += 1
            else:
                kept.append(line)

        return ToolResult(ok=True, data={"text": "".join(kept), "removed_count": removed_count})

    def cmd_split(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        text_or_error = require_text(args)
        if isinstance(text_or_error, ToolResult):
            return text_or_error
        text = text_or_error

        separator = str(args.get("separator", "\n"))
        use_regex = bool(args.get("regex"))
        limit = int(args.get("limit") or 0)
        trim_parts = bool(args.get("trim_parts", True))
        skip_empty = bool(args.get("skip_empty"))

        if use_regex:
            compiled = compile_pattern(separator, args.get("flags"))
            if isinstance(compiled, ToolResult):
                return compiled
            parts = compiled.split(text, maxsplit=limit) if limit > 0 else compiled.split(text)
        else:
            parts = text.split(separator, maxsplit=limit) if limit > 0 else text.split(separator)

        normalized = [part.strip() if trim_parts else part for part in parts]
        if skip_empty:
            normalized = [part for part in normalized if part]

        return ToolResult(ok=True, data={"parts": normalized, "count": len(normalized)})

    def cmd_join(self, args: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        parts_or_error = require_parts(args)
        if isinstance(parts_or_error, ToolResult):
            return parts_or_error
        parts = parts_or_error

        separator = str(args.get("separator", "\n"))
        skip_empty = bool(args.get("skip_empty", True))
        if skip_empty:
            parts = [part for part in parts if part]

        return ToolResult(ok=True, data={"text": separator.join(parts)})
