from __future__ import annotations

import json
from typing import Any

import redis

from app.config import get_settings


def _client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def _session_key(agent_slug: str, session_id: str) -> str:
    return f"eva:web_client:{agent_slug}:{session_id}"


def _outbox_key(agent_slug: str, session_id: str) -> str:
    return f"eva:web_client:outbox:{agent_slug}:{session_id}"


class WebClientSessionStore:
    def upsert_snapshot(
        self,
        *,
        agent_slug: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> None:
        client = _client()
        existing_raw = client.get(_session_key(agent_slug, session_id))
        existing: dict[str, Any] = {}
        if existing_raw:
            try:
                existing = json.loads(existing_raw)
            except json.JSONDecodeError:
                existing = {}
        merged = {**existing, **payload, "sessionId": session_id}
        client.set(_session_key(agent_slug, session_id), json.dumps(merged), ex=60 * 60 * 24 * 7)

    def get_snapshot(self, *, agent_slug: str, session_id: str) -> dict[str, Any] | None:
        client = _client()
        raw = client.get(_session_key(agent_slug, session_id))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def push_outbox(
        self,
        *,
        agent_slug: str,
        session_id: str,
        message: dict[str, Any],
        max_items: int = 100,
    ) -> None:
        client = _client()
        key = _outbox_key(agent_slug, session_id)
        client.lpush(key, json.dumps(message))
        client.ltrim(key, 0, max_items - 1)
        client.expire(key, 60 * 60 * 24)

    def list_outbox(self, *, agent_slug: str, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        client = _client()
        rows = client.lrange(_outbox_key(agent_slug, session_id), 0, max(0, limit - 1))
        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                item = json.loads(row)
                if isinstance(item, dict):
                    result.append(item)
            except json.JSONDecodeError:
                continue
        return result
