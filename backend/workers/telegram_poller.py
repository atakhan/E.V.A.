from __future__ import annotations

import logging
import time

import httpx
from sqlalchemy import select

from app.api.channels.telegram_utils import default_skill_id, normalize_telegram_update
from definition.catalog.builtin_events import channel_message_received
from definition.services.agent_service import AgentService
from runtime.tool_instance_resolver import find_instance_by_credential
from app.config import get_settings
from app.deps import session_scope
from infrastructure.crypto.secrets import decrypt_secret
from infrastructure.models.tables import AgentRow, ToolCredentialRow
from infrastructure.redis.event_bus import _client, publish_event

logger = logging.getLogger(__name__)


def _offset_key(credential_id: str) -> str:
    return f"eva:tg:offset:{credential_id}"


def _load_offset(credential_id: str) -> int:
    client = _client()
    raw = client.get(_offset_key(credential_id))
    return int(raw) if raw else 0


def _save_offset(credential_id: str, offset: int) -> None:
    client = _client()
    client.set(_offset_key(credential_id), str(offset))


def _active_telegram_credentials(session) -> list[tuple[ToolCredentialRow, str]]:
    rows = session.execute(
        select(ToolCredentialRow, AgentRow.slug)
        .join(AgentRow, AgentRow.id == ToolCredentialRow.agent_id)
        .where(ToolCredentialRow.tool_id == "telegram")
    )
    return [(row[0], row[1]) for row in rows]


def _is_pollable_credential(credential: ToolCredentialRow, token: str) -> bool:
    meta = credential.meta or {}
    if meta.get("dev_stub") is True:
        return False
    if "TEST-DEV-TOKEN" in token or token.startswith("000000:"):
        return False
    return True


def _poll_credential(credential: ToolCredentialRow, agent_slug: str, token: str) -> int:
    offset = _load_offset(credential.id)
    try:
        response = httpx.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": offset, "timeout": 0, "limit": 50},
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("getUpdates request failed for credential %s: %s", credential.id, exc)
        return 0

    if response.status_code in (401, 404):
        logger.warning(
            "Skipping credential %s (%s): Telegram returned %s — check bot token",
            credential.id,
            agent_slug,
            response.status_code,
        )
        return 0

    if not response.is_success:
        logger.warning(
            "getUpdates HTTP %s for credential %s: %s",
            response.status_code,
            credential.id,
            response.text[:200],
        )
        return 0

    body = response.json()
    if not body.get("ok"):
        logger.warning("getUpdates failed for %s: %s", credential.id, body)
        return 0

    processed = 0
    for update in body.get("result", []):
        update_id = update.get("update_id")
        if update_id is not None:
            _save_offset(credential.id, int(update_id) + 1)

        payload = normalize_telegram_update(update)
        if payload is None:
            continue

        instance_id: str | None = None
        with session_scope() as lookup_session:
            agent_doc = AgentService(lookup_session).get_agent_by_slug(agent_slug)
            if agent_doc:
                instance_id = find_instance_by_credential(agent_doc, str(credential.id))

        event = channel_message_received(
            conversation_id=str(payload.get("conversation_id") or ""),
            text=str(payload.get("text") or ""),
            source="telegram",
            message_id=str(payload["message_id"]) if payload.get("message_id") else None,
            sender_id=str(payload["sender_id"]) if payload.get("sender_id") else None,
            tool_instance_id=instance_id,
            tool_type_id="telegram",
        )
        skill_id = default_skill_id(agent_slug)
        publish_event(event, agent_slug=agent_slug, skill_id=skill_id)
        processed += 1
    return processed


def poll_once() -> int:
    processed = 0
    with session_scope() as session:
        for credential, agent_slug in _active_telegram_credentials(session):
            secret = decrypt_secret(credential.secret_encrypted)
            token = secret.get("bot_token")
            if not token or not _is_pollable_credential(credential, str(token)):
                continue
            processed += _poll_credential(credential, agent_slug, str(token))
    return processed


def run_poller(interval_sec: float = 2.0) -> None:
    settings = get_settings()
    if not settings.telegram_polling:
        logger.info("Telegram polling disabled (EVA_TELEGRAM_POLLING=false)")
        return

    logger.info("Telegram poller started")
    while True:
        try:
            count = poll_once()
            if count:
                logger.info("Enqueued %s telegram updates", count)
        except Exception:
            logger.exception("Telegram poll iteration failed")
        time.sleep(interval_sec)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_poller()
