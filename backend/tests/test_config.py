import pytest

from app.config import Settings, SettingsError


def test_missing_env_fails(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SettingsError, match="DATABASE_URL"):
        Settings()


def test_empty_required_env_fails(monkeypatch):
    monkeypatch.setenv("EVA_EVENT_STREAM", "")
    with pytest.raises(SettingsError, match="EVA_EVENT_STREAM"):
        Settings()


def test_empty_default_skill_ids_allowed(monkeypatch):
    monkeypatch.setenv("EVA_DEFAULT_SKILL_IDS", "")
    settings = Settings()
    assert settings.default_skill_ids == ""
