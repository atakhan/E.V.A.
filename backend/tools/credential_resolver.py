from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from definition.services.credential_service import CredentialService


def get_credential_secret(session: Session, agent_id: str, credential_id: str) -> dict[str, Any]:
    return CredentialService(session).get_secret(agent_id, credential_id)


def get_telegram_token_for_binding(
    session: Session,
    agent_id: str,
    binding: dict[str, Any],
) -> str | None:
    credential_id = binding.get("credentialId")
    if not credential_id:
        return None
    secret = get_credential_secret(session, agent_id, credential_id)
    token = secret.get("bot_token")
    return str(token) if token else None


def get_polza_api_key_for_binding(
    session: Session,
    agent_id: str,
    binding: dict[str, Any],
) -> str | None:
    credential_id = binding.get("credentialId")
    if not credential_id:
        return None
    secret = get_credential_secret(session, agent_id, credential_id)
    key = secret.get("api_key")
    return str(key) if key else None


def get_web_client_secret_for_binding(
    session: Session,
    agent_id: str,
    binding: dict[str, Any],
) -> dict[str, Any] | None:
    credential_id = binding.get("credentialId")
    if not credential_id:
        return None
    return get_credential_secret(session, agent_id, credential_id)


def parse_binding_config(binding: dict[str, Any]) -> dict[str, Any]:
    """Parse optional JSON from configNote for tool-specific settings (e.g. model)."""
    note = binding.get("configNote") or binding.get("config") or ""
    if isinstance(note, dict):
        return dict(note)
    text = str(note).strip()
    if not text.startswith("{"):
        return {}
    try:
        import json

        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}
