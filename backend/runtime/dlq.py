from __future__ import annotations

import json

from app.config import get_settings
from infrastructure.redis.event_bus import _client

ATTEMPT_PREFIX = "eva:msg_attempts:"
DLQ_STREAM_SUFFIX = ":dlq"


def increment_attempt(message_id: str) -> int:
    client = _client()
    key = f"{ATTEMPT_PREFIX}{message_id}"
    return int(client.incr(key))


def move_to_dlq(fields: dict, *, reason: str, attempts: int) -> str:
    settings = get_settings()
    client = _client()
    stream = f"{settings.event_stream}{DLQ_STREAM_SUFFIX}"
    payload = dict(fields)
    payload["dlq_reason"] = reason
    payload["dlq_attempts"] = str(attempts)
    return client.xadd(stream, payload)


def max_delivery_attempts() -> int:
    return get_settings().event_max_attempts
