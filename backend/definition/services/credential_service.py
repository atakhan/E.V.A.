from __future__ import annotations

import uuid
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from infrastructure.crypto.secrets import decrypt_secret, encrypt_secret
from infrastructure.models.tables import AgentRow, ToolCredentialRow


class CredentialService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _agent(self, slug: str) -> AgentRow:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")
        return agent

    def list_credentials(self, slug: str, tool_id: str | None = None) -> list[dict[str, Any]]:
        agent = self._agent(slug)
        query = select(ToolCredentialRow).where(ToolCredentialRow.agent_id == agent.id)
        if tool_id:
            query = query.where(ToolCredentialRow.tool_id == tool_id)
        rows = self.session.scalars(query.order_by(ToolCredentialRow.created_at.desc())).all()
        return [self._public_view(row) for row in rows]

    def create_credential(
        self,
        slug: str,
        *,
        tool_id: str,
        name: str,
        secret: dict[str, Any],
    ) -> dict[str, Any]:
        agent = self._agent(slug)
        row = ToolCredentialRow(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            tool_id=tool_id,
            name=name.strip() or tool_id,
            secret_encrypted=encrypt_secret(secret),
            meta={},
        )
        self.session.add(row)
        self.session.flush()
        return self._public_view(row)

    def delete_credential(self, slug: str, credential_id: str) -> None:
        agent = self._agent(slug)
        row = self.session.scalar(
            select(ToolCredentialRow).where(
                ToolCredentialRow.id == credential_id,
                ToolCredentialRow.agent_id == agent.id,
            )
        )
        if row is None:
            raise KeyError(f"Credential '{credential_id}' not found")
        self.session.delete(row)

    def get_secret(self, agent_id: str, credential_id: str) -> dict[str, Any]:
        row = self.session.scalar(
            select(ToolCredentialRow).where(
                ToolCredentialRow.id == credential_id,
                ToolCredentialRow.agent_id == agent_id,
            )
        )
        if row is None:
            raise KeyError(f"Credential '{credential_id}' not found")
        return decrypt_secret(row.secret_encrypted)

    def verify_telegram(self, slug: str, credential_id: str) -> dict[str, Any]:
        agent = self._agent(slug)
        row = self.session.scalar(
            select(ToolCredentialRow).where(
                ToolCredentialRow.id == credential_id,
                ToolCredentialRow.agent_id == agent.id,
                ToolCredentialRow.tool_id == "telegram",
            )
        )
        if row is None:
            raise KeyError(f"Credential '{credential_id}' not found")

        secret = decrypt_secret(row.secret_encrypted)
        token = secret.get("bot_token", "")
        if not token:
            raise ValueError("bot_token is missing in credential")

        response = httpx.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=15.0,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise ValueError(body.get("description", "Telegram getMe failed"))

        result = body["result"]
        row.meta = {
            "bot_id": result.get("id"),
            "bot_username": result.get("username"),
            "bot_name": result.get("first_name"),
        }
        self.session.flush()
        return self._public_view(row)

    def set_telegram_webhook(self, slug: str, credential_id: str) -> dict[str, Any]:
        from app.config import get_settings

        settings = get_settings()
        if not settings.webhook_base:
            raise ValueError("EVA_WEBHOOK_BASE is not configured")

        agent = self._agent(slug)
        row = self.session.scalar(
            select(ToolCredentialRow).where(
                ToolCredentialRow.id == credential_id,
                ToolCredentialRow.agent_id == agent.id,
                ToolCredentialRow.tool_id == "telegram",
            )
        )
        if row is None:
            raise KeyError(f"Credential '{credential_id}' not found")

        secret = decrypt_secret(row.secret_encrypted)
        token = secret.get("bot_token", "")
        url = f"{settings.webhook_base.rstrip('/')}/api/channels/telegram/{slug}"
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": url},
            timeout=15.0,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise ValueError(body.get("description", "setWebhook failed"))
        return {"ok": True, "url": url}

    @staticmethod
    def _public_view(row: ToolCredentialRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "toolId": row.tool_id,
            "name": row.name,
            "meta": row.meta or {},
            "createdAt": row.created_at.isoformat(),
            "updatedAt": row.updated_at.isoformat(),
        }
