from __future__ import annotations

import os
from functools import lru_cache


class SettingsError(RuntimeError):
    pass


def _require(name: str) -> str:
    if name not in os.environ:
        raise SettingsError(f"missing required environment variable: {name}")
    return os.environ[name]


def _require_nonempty(name: str) -> str:
    value = _require(name).strip()
    if not value:
        raise SettingsError(f"empty required environment variable: {name}")
    return value


def _require_bool(name: str) -> bool:
    raw = _require_nonempty(name).lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    raise SettingsError(f"invalid boolean for {name}: {raw!r}")


def _require_int(name: str) -> int:
    raw = _require_nonempty(name)
    try:
        return int(raw)
    except ValueError as exc:
        raise SettingsError(f"invalid integer for {name}: {raw!r}") from exc


def _require_choice(name: str, allowed: frozenset[str]) -> str:
    value = _require_nonempty(name).lower()
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise SettingsError(f"invalid value for {name}: {value!r} (expected {choices})")
    return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


class Settings:
    def __init__(self) -> None:
        self.database_url = _require_nonempty("DATABASE_URL")
        self.redis_url = _require_nonempty("REDIS_URL")
        self.event_stream = _require_nonempty("EVA_EVENT_STREAM")
        self.event_consumer_group = _require_nonempty("EVA_EVENT_CONSUMER_GROUP")
        self.auto_migrate = _require_bool("EVA_AUTO_MIGRATE")
        self.credentials_key = _require("EVA_CREDENTIALS_KEY")
        self.webhook_base = _require("EVA_WEBHOOK_BASE")
        self.telegram_mode = _require_choice("EVA_TELEGRAM_MODE", frozenset({"stub", "real"}))
        self.telegram_polling = _require_bool("EVA_TELEGRAM_POLLING")
        self.polza_mode = _require_choice("EVA_POLZA_MODE", frozenset({"stub", "real"}))
        self.polza_api_base = _require_nonempty("POLZA_API_BASE")
        self.polza_default_model = _require_nonempty("POLZA_DEFAULT_MODEL")
        self.default_skill_ids = _require("EVA_DEFAULT_SKILL_IDS")
        self.public_url = _require_nonempty("EVA_PUBLIC_URL")
        self.web_client_docker_host = _require_nonempty("EVA_WEB_CLIENT_DOCKER_HOST")
        self.web_client_docker_rewrite = _require_bool("EVA_WEB_CLIENT_DOCKER_REWRITE")
        self.tool_input_validation = _require_choice(
            "EVA_TOOL_INPUT_VALIDATION",
            frozenset({"warn", "strict", "off"}),
        )
        self.event_max_attempts = _require_int("EVA_EVENT_MAX_ATTEMPTS")
        self.prune_ephemeral_agents = _require_bool("EVA_PRUNE_EPHEMERAL_AGENTS")
