from __future__ import annotations

from typing import Any

from domain.events import ToolResult

MAX_TEXT_LENGTH = 1_000_000
DEFAULT_FIND_ALL_LIMIT = 100
MAX_FIND_ALL_LIMIT = 10_000


def clamp_limit(value: Any, *, default: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return min(parsed, maximum)


def require_text(args: dict[str, Any], *, field: str = "text") -> str | ToolResult:
    raw = args.get(field)
    if raw is None:
        return ToolResult(ok=False, error=f"text.{field} is required")
    text = str(raw)
    if len(text) > MAX_TEXT_LENGTH:
        return ToolResult(ok=False, error=f"text exceeds maximum length of {MAX_TEXT_LENGTH}")
    return text


def require_parts(args: dict[str, Any]) -> list[str] | ToolResult:
    raw = args.get("parts")
    if not isinstance(raw, list):
        return ToolResult(ok=False, error="text.parts must be an array of strings")
    parts = [str(item) for item in raw]
    total_len = sum(len(part) for part in parts)
    if total_len > MAX_TEXT_LENGTH:
        return ToolResult(ok=False, error=f"text parts exceed maximum total length of {MAX_TEXT_LENGTH}")
    return parts
