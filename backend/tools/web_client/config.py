from __future__ import annotations

import json
from typing import Any

from definition.catalog.web_client_defaults import WEB_CLIENT_DEFAULTS


def parse_web_client_binding_config(binding: dict[str, Any]) -> dict[str, Any]:
    raw = binding.get("configNote") or binding.get("config") or ""
    data: dict[str, Any] = {}
    if isinstance(raw, dict):
        data = dict(raw)
    elif isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            pass

    merged = {**WEB_CLIENT_DEFAULTS, **data}
    merged["timeoutSec"] = int(merged.get("timeoutSec") or WEB_CLIENT_DEFAULTS["timeoutSec"])
    return merged


def resolve_backend_url(base_url: str, docker_rewrite: bool, docker_host: str) -> str:
    url = base_url.rstrip("/")
    if not docker_rewrite:
        return url
    for local in ("localhost", "127.0.0.1"):
        if f"://{local}" in url:
            return url.replace(f"://{local}", f"://{docker_host}")
    return url
