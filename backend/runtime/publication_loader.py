from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from definition.services.agent_service import AgentService


def load_published_agent_body(session: Session, agent_slug: str) -> dict[str, Any] | None:
    publication = AgentService(session).get_latest_publication(agent_slug)
    if publication is None:
        return None
    body = publication.body
    return body if isinstance(body, dict) else None
