from __future__ import annotations

import secrets
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
        if tool_id == "web_client":
            secret = dict(secret)
            if not secret.get("inbound_api_key"):
                secret["inbound_api_key"] = secrets.token_urlsafe(32)
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
        view = self._public_view(row)
        if tool_id == "web_client":
            view["oneTimeSecrets"] = {
                "inboundApiKey": secret.get("inbound_api_key"),
            }
        return view

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

    def verify_credential(self, slug: str, credential_id: str) -> dict[str, Any]:
        agent = self._agent(slug)
        row = self.session.scalar(
            select(ToolCredentialRow).where(
                ToolCredentialRow.id == credential_id,
                ToolCredentialRow.agent_id == agent.id,
            )
        )
        if row is None:
            raise KeyError(f"Credential '{credential_id}' not found")

        if row.tool_id == "telegram":
            return self.verify_telegram(slug, credential_id)
        if row.tool_id == "polza_ai_llm":
            return self.verify_polza(slug, credential_id)
        if row.tool_id == "web_client":
            return self.verify_web_client(slug, credential_id)
        raise ValueError(f"Verify is not supported for tool '{row.tool_id}'")

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

    def verify_polza(self, slug: str, credential_id: str) -> dict[str, Any]:
        from app.config import get_settings
        from tools.polza import PolzaApiError, PolzaClient

        agent = self._agent(slug)
        row = self.session.scalar(
            select(ToolCredentialRow).where(
                ToolCredentialRow.id == credential_id,
                ToolCredentialRow.agent_id == agent.id,
                ToolCredentialRow.tool_id == "polza_ai_llm",
            )
        )
        if row is None:
            raise KeyError(f"Credential '{credential_id}' not found")

        secret = decrypt_secret(row.secret_encrypted)
        api_key = secret.get("api_key", "")
        if not api_key:
            raise ValueError("api_key is missing in credential")

        settings = get_settings()
        client = PolzaClient(str(api_key), base_url=settings.polza_api_base)
        try:
            balance = client.get_balance()
        except PolzaApiError as exc:
            raise ValueError(str(exc)) from exc

        amount = balance.get("amount")
        row.meta = {
            **(row.meta or {}),
            "verified": True,
            "balance_amount": str(amount) if amount is not None else None,
            "provider": "polza.ai",
        }
        self.session.flush()
        return self._public_view(row)

    def verify_web_client(self, slug: str, credential_id: str) -> dict[str, Any]:
        from app.config import get_settings
        from definition.services.agent_service import AgentService
        from tools.web_client import WebClientHttp, WebClientHttpError, parse_web_client_binding_config

        agent = self._agent(slug)
        row = self.session.scalar(
            select(ToolCredentialRow).where(
                ToolCredentialRow.id == credential_id,
                ToolCredentialRow.agent_id == agent.id,
                ToolCredentialRow.tool_id == "web_client",
            )
        )
        if row is None:
            raise KeyError(f"Credential '{credential_id}' not found")

        secret = decrypt_secret(row.secret_encrypted)
        base_url = str(secret.get("backend_base_url") or "").strip()
        outbound_key = str(secret.get("outbound_api_key") or "")
        if not base_url:
            raise ValueError("backend_base_url is missing in credential")

        agent_doc = AgentService(self.session).get_agent_by_slug(slug) or {}
        binding = next(
            (item for item in agent_doc.get("tools", []) if item.get("toolId") == "web_client"),
            {},
        )
        config = parse_web_client_binding_config(binding)
        settings = get_settings()
        client = WebClientHttp(
            base_url=base_url,
            outbound_api_key=outbound_key,
            config=config,
            docker_rewrite=settings.web_client_docker_rewrite,
            docker_host=settings.web_client_docker_host,
        )
        try:
            body = client.health()
        except WebClientHttpError as exc:
            raise ValueError(str(exc)) from exc

        row.meta = {
            **(row.meta or {}),
            "verified": True,
            "health_status": body.get("_status_code", 200),
            "latency_ms": body.get("_duration_ms"),
            "backend_base_url": base_url,
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
