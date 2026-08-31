from __future__ import annotations

import time
from contextlib import contextmanager

from app.config import get_settings
from infrastructure.redis.event_bus import _client

LOCK_PREFIX = "eva:corr_lock:"
LOCK_TTL_SEC = 30


@contextmanager
def correlation_lock(correlation_key: str):
    """Serialize event processing per correlation key."""
    if not correlation_key:
        yield
        return

    client = _client()
    lock_key = f"{LOCK_PREFIX}{correlation_key}"
    token = f"{time.time()}"
    acquired = client.set(lock_key, token, nx=True, ex=LOCK_TTL_SEC)
    if not acquired:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            time.sleep(0.05)
            acquired = client.set(lock_key, token, nx=True, ex=LOCK_TTL_SEC)
            if acquired:
                break
    try:
        yield
    finally:
        if acquired:
            current = client.get(lock_key)
            if current == token:
                client.delete(lock_key)
