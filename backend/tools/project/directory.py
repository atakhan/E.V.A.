from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from definition.agent_protocol import RECEIVED
from definition.interaction_manifest import normalize_interaction_manifest
from definition.mappers.event_mapper import create_domain_event
from definition.services.agent_service import AgentService
from definition.services.project_service import ProjectService
from infrastructure.models.tables import ProjectRow
from infrastructure.redis.event_bus import publish_event


class SqlAgentDirectory:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._agents = AgentService(session)
        self._projects = ProjectService(session)

    def agent_exists(self, agent_slug: str) -> bool:
        return self._agents.get_agent_row(agent_slug) is not None

    def interaction_manifest(self, agent_slug: str) -> dict[str, Any]:
        """Connect policy from the draft — applies without publishing."""
        body = self._agents.get_agent_by_slug(agent_slug)
        if body is None:
            return normalize_interaction_manifest(None)
        memory = body.get("memory") if isinstance(body.get("memory"), dict) else {}
        return normalize_interaction_manifest(memory.get("interaction"))

    def project_of(self, agent_slug: str) -> str | None:
        body = self._agents.get_agent_by_slug(agent_slug)
        if body and body.get("kind") == "runtime" and body.get("projectSlug"):
            return str(body["projectSlug"])
        for project in self._projects.list_projects():
            slugs = {item.get("agentSlug") for item in project.get("agents") or []}
            if agent_slug in slugs:
                return str(project["slug"])
            if project.get("runtimeAgentSlug") == agent_slug:
                return str(project["slug"])
        return None

    def runtime_agent(self, project_slug: str) -> str | None:
        row = self._projects._find_runtime(project_slug)
        return row.slug if row is not None else None

    def hosts(self, project_slug: str, agent_slug: str) -> bool:
        if self.runtime_agent(project_slug) == agent_slug:
            return True
        row = self._session.scalar(select(ProjectRow).where(ProjectRow.slug == project_slug))
        if row is None:
            return False
        return any(
            isinstance(item, dict) and item.get("agentSlug") == agent_slug for item in (row.agents or [])
        )

    def published_skills(self, agent_slug: str) -> list[dict[str, Any]] | None:
        publication = self._agents.get_latest_publication(agent_slug)
        if publication is None or not isinstance(publication.body, dict):
            return None
        skills = publication.body.get("skills") or []
        return [skill for skill in skills if isinstance(skill, dict)]

    def deliver(
        self,
        agent_slug: str,
        skill_id: str,
        payload: dict[str, Any],
        *,
        source: str = "project",
    ) -> None:
        event = create_domain_event(
            RECEIVED,
            source=source,
            payload=payload,
            correlation={"conversation_id": payload.get("conversation_id")},
        )
        publish_event(event, agent_slug=agent_slug, skill_id=skill_id)
