from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.channels.event_ingress import enqueue_channel_event
from app.api.channels.telegram_utils import default_skill_id
from definition.services.credential_service import CredentialService
from definition.services.agent_service import AgentService
from runtime.tool_instance_resolver import find_instance_by_credential
from infrastructure.stores.web_client_store import WebClientSessionStore
from infrastructure.models.tables import AgentRow, ToolCredentialRow
from tools.web_client import parse_web_client_binding_config

router = APIRouter(prefix="/api/channels", tags=["channels"])


class WebEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId")
    type: str = "channel.message.received"
    skill_id: str | None = Field(default=None, alias="skillId")
    payload: dict[str, Any] = Field(default_factory=dict)


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def _verify_inbound_key(session: Session, agent_slug: str, token: str | None) -> ToolCredentialRow:
    if not token:
        raise HTTPException(status_code=401, detail="Authorization required")

    agent = session.scalar(select(AgentRow).where(AgentRow.slug == agent_slug))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.archived_at is not None:
        raise HTTPException(status_code=409, detail="Agent is archived")

    rows = session.scalars(
        select(ToolCredentialRow).where(
            ToolCredentialRow.agent_id == agent.id,
            ToolCredentialRow.tool_id == "web_client",
        )
    ).all()

    service = CredentialService(session)
    for row in rows:
        secret = service.get_secret(agent.id, row.id)
        inbound = secret.get("inbound_api_key")
        if inbound and str(inbound) == token:
            return row

    raise HTTPException(status_code=401, detail="Invalid inbound API key")


def _enqueue_inbound(
    *,
    agent_slug: str,
    payload: dict[str, Any],
    event_type: str = "channel.message.received",
    skill_id: str | None = None,
    source: str = "web_client",
    tool_instance_id: str | None = None,
) -> dict[str, Any]:
    resolved_skill = skill_id or default_skill_id(agent_slug)
    return enqueue_channel_event(
        agent_slug=agent_slug,
        payload=payload,
        event_type=event_type,
        skill_id=resolved_skill,
        source=source,
        tool_instance_id=tool_instance_id,
        tool_type_id="web_client" if tool_instance_id else None,
    )


@router.post("/web/{agent_slug}/events")
async def web_events(
    agent_slug: str,
    body: WebEventRequest,
    authorization: str | None = Header(default=None),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    token = _extract_bearer(authorization)
    credential_row = _verify_inbound_key(session, agent_slug, token)

    instance_id: str | None = None
    agent_doc = AgentService(session).get_agent_by_slug(agent_slug)
    if agent_doc:
        instance_id = find_instance_by_credential(agent_doc, str(credential_row.id))

    payload = dict(body.payload)
    payload.setdefault("conversation_id", body.session_id)
    if "text" not in payload and isinstance(payload.get("message"), str):
        payload["text"] = payload["message"]

    WebClientSessionStore().upsert_snapshot(
        agent_slug=agent_slug,
        session_id=body.session_id,
        payload={
            "conversation_id": body.session_id,
            "lastMessage": payload.get("text", ""),
            "context": payload.get("context") if isinstance(payload.get("context"), dict) else payload,
        },
    )

    return _enqueue_inbound(
        agent_slug=agent_slug,
        payload=payload,
        event_type=body.type,
        skill_id=body.skill_id,
        tool_instance_id=instance_id,
    )


@router.get("/web/{agent_slug}/sessions/{session_id}/outbox")
def web_outbox(
    agent_slug: str,
    session_id: str,
    authorization: str | None = Header(default=None),
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    token = _extract_bearer(authorization)
    _verify_inbound_key(session, agent_slug, token)
    messages = WebClientSessionStore().list_outbox(agent_slug=agent_slug, session_id=session_id)
    return {"ok": True, "messages": messages}
