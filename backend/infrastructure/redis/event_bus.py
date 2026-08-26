from __future__ import annotations

import json
import uuid
from typing import Any

import redis

from app.config import get_settings


def _client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def publish_event(event: dict[str, Any]) -> str:
    settings = get_settings()
    client = _client()
    message_id = str(uuid.uuid4())
    payload = {"id": message_id, **event}
    client.xadd(settings.event_stream, {"data": json.dumps(payload)})
    return message_id


def ensure_consumer_group() -> None:
    settings = get_settings()
    client = _client()
    try:
        client.xgroup_create(settings.event_stream, settings.event_consumer_group, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
