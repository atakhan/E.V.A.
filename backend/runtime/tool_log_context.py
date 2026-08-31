from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "bot_token",
        "token",
        "secret",
        "password",
        "authorization",
        "outbound_api_key",
        "inbound_api_key",
        "inboundapikey",
        "outboundapikey",
    }
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    return normalized in _SENSITIVE_KEYS or normalized.endswith("_key") or normalized.endswith("_token")


def sanitize_for_log(value: Any, *, depth: int = 0) -> Any:
    if depth > 8:
        return "…"
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                sanitized[str(key)] = "***"
            else:
                sanitized[str(key)] = sanitize_for_log(item, depth=depth + 1)
        return sanitized
    if isinstance(value, list):
        return [sanitize_for_log(item, depth=depth + 1) for item in value[:50]]
    if isinstance(value, str):
        return value if len(value) <= 4000 else f"{value[:4000]}…"
    return value


@dataclass
class ToolLogContext:
    session: Session
    agent_id: str
    agent_slug: str = ""
    credential_by_instance: dict[str, str] | None = None

    def credential_for_tool(self, instance_id: str, tool: Any) -> str | None:
        explicit = getattr(tool, "credential_id", None)
        if explicit:
            return str(explicit)
        if self.credential_by_instance and instance_id in self.credential_by_instance:
            return self.credential_by_instance[instance_id]
        return None
