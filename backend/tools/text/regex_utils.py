from __future__ import annotations

import re
from re import Pattern
from typing import Any

from domain.events import ToolResult


def parse_flags(flags: Any) -> int:
    if not flags:
        return 0
    flag_text = str(flags)
    result = 0
    if "i" in flag_text:
        result |= re.IGNORECASE
    if "m" in flag_text:
        result |= re.MULTILINE
    if "s" in flag_text:
        result |= re.DOTALL
    return result


def compile_pattern(pattern: str, flags: Any) -> Pattern[str] | ToolResult:
    try:
        return re.compile(pattern, parse_flags(flags))
    except re.error as exc:
        return ToolResult(ok=False, error=f"invalid_pattern: {exc}")
