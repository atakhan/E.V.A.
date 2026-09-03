from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.channels.event_ingress import enqueue_channel_event
from app.api.channels.telegram_utils import normalize_telegram_update
from infrastructure.models.tables import AgentRow
from runtime.skill_resolver import resolve_skill_for_agent_slug

router = APIRouter(prefix="/api/channels", tags=["channels"])


def _db_session():
    from app.deps import session_scope

    with session_scope() as session:
        yield session


def _ensure_agent_active(session: Session, agent_slug: str) -> None:
    agent = session.scalar(select(AgentRow).where(AgentRow.slug == agent_slug))
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.archived_at is not None:
        raise HTTPException(status_code=409, detail="Agent is archived")


def _enqueue_inbound(
    *,
    session: Session,
    agent_slug: str,
    payload: dict[str, Any],
    event_type: str = "channel.message.received",
) -> dict[str, Any]:
    resolution = resolve_skill_for_agent_slug(
        session,
        agent_slug=agent_slug,
        event_type=event_type,
    )
    if not resolution.ok:
        raise HTTPException(status_code=422, detail=resolution.error)
    return enqueue_channel_event(
        agent_slug=agent_slug,
        payload=payload,
        event_type=event_type,
        skill_id=resolution.skill_id,
        source="telegram",
    )


@router.post("/telegram/{agent_slug}")
async def telegram_webhook(
    agent_slug: str,
    request: Request,
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    _ensure_agent_active(session, agent_slug)
    body = await request.json()
    if "message" in body or "edited_message" in body:
        payload = normalize_telegram_update(body)
        if payload is None:
            return {"ok": True, "ignored": True}
        return _enqueue_inbound(session=session, agent_slug=agent_slug, payload=payload)

    # Legacy simplified payload for tests/manual calls
    conversation_id = body.get("conversation_id") or body.get("chat_id")
    message = body.get("message")
    if message:
        conversation_id = conversation_id or message.get("chat_id")
        text = message.get("text", body.get("text", ""))
    else:
        text = body.get("text", "")

    if not conversation_id:
        return {"ok": False, "error": "conversation_id or chat_id required"}

    return _enqueue_inbound(
        session=session,
        agent_slug=agent_slug,
        payload={
            "conversation_id": str(conversation_id),
            "text": text,
        },
    )


@router.post("/telegram")
async def telegram_webhook_legacy(
    request: Request,
    session: Session = Depends(_db_session),
) -> dict[str, Any]:
    """Backward-compatible endpoint defaulting to foreman agent."""
    return await telegram_webhook("foreman", request, session)
