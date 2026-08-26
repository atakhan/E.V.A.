from __future__ import annotations

import os
from functools import lru_cache


@lru_cache
def get_settings() -> "Settings":
    return Settings()


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://eva:eva@postgres:5432/eva",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    event_stream: str = os.getenv("EVA_EVENT_STREAM", "eva:events")
    event_consumer_group: str = os.getenv("EVA_EVENT_CONSUMER_GROUP", "eva-runtime")
    auto_migrate: bool = os.getenv("EVA_AUTO_MIGRATE", "true").lower() in ("1", "true", "yes")
    credentials_key: str = os.getenv("EVA_CREDENTIALS_KEY", "")
    webhook_base: str = os.getenv("EVA_WEBHOOK_BASE", "")
    telegram_mode: str = os.getenv("EVA_TELEGRAM_MODE", "stub")
    telegram_polling: bool = os.getenv("EVA_TELEGRAM_POLLING", "false").lower() in ("1", "true", "yes")
    default_skill_ids: str = os.getenv("EVA_DEFAULT_SKILL_IDS", "foreman=process_foreman_request")
