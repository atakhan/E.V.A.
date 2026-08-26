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
