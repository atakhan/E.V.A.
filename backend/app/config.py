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
    polza_mode: str = os.getenv("EVA_POLZA_MODE", "real")
    polza_api_base: str = os.getenv("POLZA_API_BASE", "https://polza.ai/api/v1")
    polza_default_model: str = os.getenv("POLZA_DEFAULT_MODEL", "openai/gpt-4o-mini")
    default_skill_ids: str = os.getenv("EVA_DEFAULT_SKILL_IDS", "foreman=process_foreman_request")
    public_url: str = os.getenv("EVA_PUBLIC_URL", "http://localhost:8000")
    web_client_docker_host: str = os.getenv("EVA_WEB_CLIENT_DOCKER_HOST", "host.docker.internal")
    web_client_docker_rewrite: bool = os.getenv("EVA_WEB_CLIENT_DOCKER_REWRITE", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    seed_demo_agents: bool = os.getenv("EVA_SEED_DEMO_AGENTS", "true").lower() in ("1", "true", "yes")
    tool_input_validation: str = os.getenv("EVA_TOOL_INPUT_VALIDATION", "warn")
    event_max_attempts: int = int(os.getenv("EVA_EVENT_MAX_ATTEMPTS", "5"))
    prune_ephemeral_agents: bool = os.getenv("EVA_PRUNE_EPHEMERAL_AGENTS", "true").lower() in (
        "1",
        "true",
        "yes",
    )
