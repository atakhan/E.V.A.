from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from definition.validation.validate_agent import validate_agent
from infrastructure.models.tables import AgentDraftRow, AgentPublicationRow, AgentRow, ToolCatalogRow, ToolCredentialRow


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_draft_body(agent: AgentRow) -> dict[str, Any]:
    now = _utcnow_iso()
    return {
        "id": agent.id,
        "slug": agent.slug,
        "name": agent.name,
        "description": agent.description,
        "createdAt": now,
        "updatedAt": now,
        "skills": [],
        "actions": [],
        "tools": [],
    }


def _merge_agent(agent: AgentRow, draft_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": agent.id,
        "slug": agent.slug,
        "name": agent.name,
        "description": agent.description,
        "createdAt": agent.created_at.isoformat(),
        "updatedAt": agent.updated_at.isoformat(),
        "skills": draft_body.get("skills", []),
        "actions": draft_body.get("actions", []),
        "tools": draft_body.get("tools", []),
    }


def _bump_patch(version: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version.strip())
    if not match:
        return "0.1.0"
    major, minor, patch = match.groups()
    return f"{major}.{minor}.{int(patch) + 1}"


class AgentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_agents(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(select(AgentRow).order_by(AgentRow.updated_at.desc())).all()
        return [
            {
                "id": row.id,
                "slug": row.slug,
                "name": row.name,
                "description": row.description,
                "createdAt": row.created_at.isoformat(),
                "updatedAt": row.updated_at.isoformat(),
            }
            for row in rows
        ]

    def get_agent_by_slug(self, slug: str) -> dict[str, Any] | None:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None or agent.draft is None:
            return None
        return _merge_agent(agent, agent.draft.body)

    def create_agent(self, *, name: str, slug: str, description: str = "") -> dict[str, Any]:
        if self.session.scalar(select(AgentRow).where(AgentRow.slug == slug)):
            raise ValueError(f"Slug '{slug}' already exists")

        agent = AgentRow(slug=slug, name=name.strip(), description=description.strip())
        self.session.add(agent)
        self.session.flush()

        body = _empty_draft_body(agent)
        draft = AgentDraftRow(agent_id=agent.id, body=body)
        self.session.add(draft)
        self.session.flush()
        return _merge_agent(agent, body)

    def upsert_draft(self, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")

        agent.name = str(payload.get("name", agent.name)).strip() or agent.name
        agent.description = str(payload.get("description", agent.description)).strip()
        agent.updated_at = datetime.now(timezone.utc)

        if agent.draft is None:
            agent.draft = AgentDraftRow(agent_id=agent.id, body={})

        body = {
            "id": agent.id,
            "slug": agent.slug,
            "name": agent.name,
            "description": agent.description,
            "createdAt": agent.created_at.isoformat(),
            "updatedAt": _utcnow_iso(),
            "skills": payload.get("skills", []),
            "actions": payload.get("actions", []),
            "tools": payload.get("tools", []),
        }
        agent.draft.body = body
        agent.draft.updated_at = datetime.now(timezone.utc)
        self.session.flush()
        return _merge_agent(agent, body)

    def delete_agent(self, slug: str) -> None:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")
        self.session.delete(agent)

    def validate_draft(self, slug: str) -> dict[str, Any]:
        agent_doc = self.get_agent_by_slug(slug)
        if agent_doc is None:
            raise KeyError(f"Agent '{slug}' not found")
        return validate_agent(agent_doc)

    def publish(self, slug: str) -> dict[str, Any]:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None or agent.draft is None:
            raise KeyError(f"Agent '{slug}' not found")

        report = validate_agent(_merge_agent(agent, agent.draft.body))
        if report["errors"] > 0:
            raise ValueError("Cannot publish agent with validation errors")

        latest = self.session.scalar(
            select(AgentPublicationRow)
            .where(AgentPublicationRow.agent_id == agent.id)
            .order_by(AgentPublicationRow.published_at.desc())
            .limit(1)
        )
        next_version = _bump_patch(latest.version) if latest else "0.1.0"
        publication = AgentPublicationRow(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            version=next_version,
            body=_merge_agent(agent, agent.draft.body),
        )
        self.session.add(publication)
        self.session.flush()
        return {
            "ok": True,
            "version": next_version,
            "publicationId": publication.id,
        }

    def list_publications(self, slug: str) -> list[dict[str, Any]]:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")
        rows = self.session.scalars(
            select(AgentPublicationRow)
            .where(AgentPublicationRow.agent_id == agent.id)
            .order_by(AgentPublicationRow.published_at.desc())
        ).all()
        return [
            {
                "id": row.id,
                "version": row.version,
                "publishedAt": row.published_at.isoformat(),
                "body": row.body,
            }
            for row in rows
        ]

    def get_latest_publication(self, slug: str) -> AgentPublicationRow | None:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None:
            return None
        return self.session.scalar(
            select(AgentPublicationRow)
            .where(AgentPublicationRow.agent_id == agent.id)
            .order_by(AgentPublicationRow.published_at.desc())
            .limit(1)
        )


def seed_tool_catalog(session: Session) -> None:
    from definition.catalog.builtin_tools import BUILTIN_TOOLS

    for tool in BUILTIN_TOOLS:
        existing = session.get(ToolCatalogRow, tool["id"])
        if existing is None:
            session.add(
                ToolCatalogRow(
                    id=tool["id"],
                    name=tool["name"],
                    description=tool.get("description", ""),
                    definition=tool,
                )
            )
        else:
            existing.name = tool["name"]
            existing.description = tool.get("description", "")
            existing.definition = tool


def seed_foreman_agent(session: Session) -> None:
    from definition.services.credential_service import CredentialService
    from scenarios.foreman_agent_document import build_foreman_agent_document

    slug = "foreman"
    doc = build_foreman_agent_document()
    service = AgentService(session)
    cred_service = CredentialService(session)

    if service.get_agent_by_slug(slug) is None:
        service.create_agent(name=doc["name"], slug=slug, description=doc.get("description", ""))

    agent = session.scalar(select(AgentRow).where(AgentRow.slug == slug))
    assert agent is not None

    credentials = cred_service.list_credentials(slug, tool_id="telegram")
    if not credentials:
        created = cred_service.create_credential(
            slug,
            tool_id="telegram",
            name="Foreman dev bot",
            secret={"bot_token": "000000:TEST-DEV-TOKEN"},
        )
        credential_id = created["id"]
        row = session.get(ToolCredentialRow, credential_id)
        if row is not None:
            row.meta = {"dev_stub": True}
            session.flush()
    else:
        credential_id = credentials[0]["id"]

    for tool in doc.get("tools", []):
        if tool.get("toolId") == "telegram":
            tool["credentialId"] = credential_id

    service.upsert_draft(slug, doc)

    publication = service.get_latest_publication(slug)
    if publication is not None and publication.body.get("skills"):
        return

    report = validate_agent(service.get_agent_by_slug(slug) or doc)
    if report["errors"] == 0:
        service.publish(slug)
