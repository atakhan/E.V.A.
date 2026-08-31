from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from definition.services.credential_service import CredentialService
from definition.services.tool_api_log_service import ToolApiLogService
from infrastructure.models.tables import AgentRow
from sqlalchemy import select
from tools.web_client import parse_web_client_binding_config, resolve_backend_url

router = APIRouter(prefix="/api/agents/{slug}/tools/web_client", tags=["web_client"])


class IntegrationInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ingress_url: str = Field(alias="ingressUrl")
    outbox_url_template: str = Field(alias="outboxUrlTemplate")
    inbound_api_key_hint: str = Field(alias="inboundApiKeyHint")
    outbound_base_url: str = Field(alias="outboundBaseUrl")
    outbound_base_url_docker: str = Field(alias="outboundBaseUrlDocker")
    paths: dict[str, Any]
    local_dev_hints: dict[str, str] = Field(alias="localDevHints")


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


def _require_agent(session: Session, slug: str) -> AgentRow:
    agent = session.scalar(select(AgentRow).where(AgentRow.slug == slug))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/integration", response_model=IntegrationInfo)
def integration_info(
    slug: str,
    credential_id: str | None = Query(default=None, alias="credentialId"),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    from definition.services.agent_service import AgentService

    _require_agent(session, slug)
    settings = get_settings()
    service = CredentialService(session)

    agent_doc = AgentService(session).get_agent_by_slug(slug) or {}
    binding = next(
        (item for item in agent_doc.get("tools", []) if item.get("toolId") == "web_client"),
        {},
    )
    resolved_id = credential_id or binding.get("credentialId")
    if not resolved_id:
        raise HTTPException(status_code=400, detail="credentialId is required")

    agent = _require_agent(session, slug)
    secret = service.get_secret(agent.id, resolved_id)
    base_url = str(secret.get("backend_base_url") or "")
    inbound_key = str(secret.get("inbound_api_key") or "")
    paths = parse_web_client_binding_config(binding if binding else {"configNote": "{}"})

    public = settings.public_url.rstrip("/")
    docker_host = settings.web_client_docker_host

    return {
        "ingressUrl": f"{public}/api/channels/web/{slug}/events",
        "outboxUrlTemplate": f"{public}/api/channels/web/{slug}/sessions/{{sessionId}}/outbox",
        "inboundApiKeyHint": f"{inbound_key[:4]}…{inbound_key[-4:]}" if len(inbound_key) > 10 else "(set)",
        "outboundBaseUrl": base_url,
        "outboundBaseUrlDocker": resolve_backend_url(base_url, True, docker_host) if base_url else "",
        "paths": paths,
        "localDevHints": {
            "ingressFromHost": f"{public}/api/channels/web/{slug}/events",
            "backendFromDocker": resolve_backend_url(base_url, True, docker_host) if base_url else "",
            "stubInCompose": "http://web-client-stub:8765",
            "stubOnHost": "http://localhost:8765",
        },
    }


@router.get("/logs")
def list_web_client_logs(
    slug: str,
    credential_id: str | None = Query(default=None, alias="credentialId"),
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(_db_session),
) -> list[dict[str, Any]]:
    agent = _require_agent(session, slug)
    return ToolApiLogService(session).list_logs(
        agent.id,
        tool_id="web_client",
        credential_id=credential_id,
        limit=limit,
    )["items"]


@router.post("/generate-inbound-key")
def generate_inbound_key() -> dict[str, str]:
    return {"inboundApiKey": secrets.token_urlsafe(32)}
