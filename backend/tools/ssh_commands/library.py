from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@dataclass(frozen=True)
class SshLibraryCommand:
    id: str
    name: str
    shell: str
    description: str = ""
    timeout_sec: int | None = None


def parse_library(config: dict[str, Any] | None) -> list[SshLibraryCommand]:
    raw = (config or {}).get("commands")
    if not isinstance(raw, list):
        return []
    items: list[SshLibraryCommand] = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        command_id = str(entry.get("id") or "").strip()
        shell = str(entry.get("shell") or "")
        if not _ID_RE.match(command_id) or not shell.strip() or command_id in seen:
            continue
        seen.add(command_id)
        name = str(entry.get("name") or "").strip() or command_id
        description = str(entry.get("description") or "").strip()
        timeout_raw = entry.get("timeoutSec")
        timeout_sec = (
            timeout_raw
            if isinstance(timeout_raw, int) and not isinstance(timeout_raw, bool) and timeout_raw > 0
            else None
        )
        items.append(
            SshLibraryCommand(
                id=command_id,
                name=name,
                shell=shell,
                description=description,
                timeout_sec=timeout_sec,
            )
        )
    return items


def library_command_ids(config: dict[str, Any] | None) -> set[str]:
    return {item.id for item in parse_library(config)}


def clamp_int(value: Any, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        try:
            if isinstance(value, str) and value.strip():
                number = int(value.strip())
            else:
                return default
        except (TypeError, ValueError):
            return default
    else:
        number = value
    return max(low, min(high, number))
