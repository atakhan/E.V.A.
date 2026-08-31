from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from definition.validation.validate_agent import validate_agent
from infrastructure.models.tables import AgentDraftRow, AgentPublicationRow, AgentRow, ToolCatalogRow, ToolCredentialRow

# Slugs created by integration tests; safe to delete on dev startup.
EPHEMERAL_AGENT_SLUG_PREFIXES = (
    "eva-test-",
    "test-agent-",
    "web-agent-",
    "cred-agent-",
)

# Demo agents seeded in dev; never pruned automatically.
DEMO_AGENT_SLUGS = frozenset({"foreman", "supplier"})


class AgentArchivedError(Exception):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Agent '{slug}' is archived")


class AgentProtectedError(Exception):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Agent '{slug}' is protected")


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
        "archivedAt": agent.archived_at.isoformat() if agent.archived_at else None,
        "skills": draft_body.get("skills", []),
        "actions": draft_body.get("actions", []),
        "tools": draft_body.get("tools", []),
    }


def _summary_from_row(row: AgentRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "archivedAt": row.archived_at.isoformat() if row.archived_at else None,
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

    def list_agents(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        query = select(AgentRow).order_by(AgentRow.updated_at.desc())
        if not include_archived:
            query = query.where(AgentRow.archived_at.is_(None))
        rows = self.session.scalars(query).all()
        return [_summary_from_row(row) for row in rows]

    def get_agent_row(self, slug: str) -> AgentRow | None:
        return self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))

    def is_archived(self, agent: AgentRow) -> bool:
        return agent.archived_at is not None

    def ensure_active(self, slug: str) -> AgentRow:
        agent = self.get_agent_row(slug)
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")
        if self.is_archived(agent):
            raise AgentArchivedError(slug)
        return agent

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
        agent = self.ensure_active(slug)

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
        agent = self.get_agent_row(slug)
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")
        self.session.delete(agent)

    def archive_agent(self, slug: str) -> dict[str, Any]:
        if slug.strip().lower() in DEMO_AGENT_SLUGS:
            raise AgentProtectedError(slug)

        agent = self.get_agent_row(slug)
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")

        if agent.archived_at is None:
            agent.archived_at = datetime.now(timezone.utc)
            agent.updated_at = datetime.now(timezone.utc)
            from infrastructure.stores.postgres_skill_run_store import PostgresSkillRunStore

            PostgresSkillRunStore(self.session).cancel_active_runs_for_agent(slug)
            self.session.flush()

        return _summary_from_row(agent)

    def unarchive_agent(self, slug: str) -> dict[str, Any]:
        agent = self.get_agent_row(slug)
        if agent is None:
            raise KeyError(f"Agent '{slug}' not found")

        if agent.archived_at is not None:
            agent.archived_at = None
            agent.updated_at = datetime.now(timezone.utc)
            self.session.flush()

        return _summary_from_row(agent)

    def is_ephemeral_slug(self, slug: str) -> bool:
        normalized = slug.strip().lower()
        if normalized in DEMO_AGENT_SLUGS:
            return False
        return any(normalized.startswith(prefix) for prefix in EPHEMERAL_AGENT_SLUG_PREFIXES)

    def validate_draft(self, slug: str) -> dict[str, Any]:
        self.ensure_active(slug)
        agent_doc = self.get_agent_by_slug(slug)
        if agent_doc is None:
            raise KeyError(f"Agent '{slug}' not found")
        return validate_agent(agent_doc)

    def publish(self, slug: str) -> dict[str, Any]:
        agent = self.ensure_active(slug)
        if agent.draft is None:
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

    def get_publication(self, slug: str, version: str) -> AgentPublicationRow | None:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == slug))
        if agent is None:
            return None
        return self.session.scalar(
            select(AgentPublicationRow).where(
                AgentPublicationRow.agent_id == agent.id,
                AgentPublicationRow.version == version,
            )
        )


def prune_ephemeral_agents(session: Session) -> list[str]:
    """Remove test agents left over from integration tests."""
    service = AgentService(session)
    removed: list[str] = []
    for summary in service.list_agents(include_archived=True):
        slug = summary["slug"]
        if service.is_ephemeral_slug(slug):
            service.delete_agent(slug)
            removed.append(slug)
    if removed:
        session.flush()
    return removed


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


def _patch_tool_credential(doc: dict[str, Any], tool_id: str, credential_id: str) -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    for tool in doc.get("tools", []):
        if not isinstance(tool, dict):
            continue
        entry = dict(tool)
        if entry.get("toolId") == tool_id:
            entry["credentialId"] = credential_id
        tools.append(entry)
    return {**doc, "tools": tools}


def _seed_agent_draft(
    service: AgentService,
    slug: str,
    template: dict[str, Any],
    *,
    tool_id: str,
    credential_id: str,
) -> None:
    """Seed demo agent without overwriting a customized draft (skills/layout in DB)."""
    existing = service.get_agent_by_slug(slug)
    if existing and existing.get("skills"):
        service.upsert_draft(slug, _patch_tool_credential(existing, tool_id, credential_id))
        return
    service.upsert_draft(slug, _patch_tool_credential(template, tool_id, credential_id))


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

    _seed_agent_draft(service, slug, doc, tool_id="telegram", credential_id=credential_id)

    publication = service.get_latest_publication(slug)
    if publication is not None and publication.body.get("skills"):
        return

    report = validate_agent(service.get_agent_by_slug(slug) or doc)
    if report["errors"] == 0:
        service.publish(slug)


def seed_supplier_agent(session: Session) -> None:
    from definition.services.credential_service import CredentialService
    from scenarios.supplier_agent_document import build_supplier_agent_document

    slug = "supplier"
    doc = build_supplier_agent_document()
    service = AgentService(session)
    cred_service = CredentialService(session)

    if service.get_agent_by_slug(slug) is None:
        service.create_agent(name=doc["name"], slug=slug, description=doc.get("description", ""))

    agent = session.scalar(select(AgentRow).where(AgentRow.slug == slug))
    assert agent is not None

    credentials = cred_service.list_credentials(slug, tool_id="web_client")
    if not credentials:
        created = cred_service.create_credential(
            slug,
            tool_id="web_client",
            name="ai_supplier dev",
            secret={
                "backend_base_url": "http://host.docker.internal:3000",
                "outbound_api_key": "dev-outbound-key",
                "inbound_api_key": "dev-inbound-key",
            },
        )
        credential_id = created["id"]
        row = session.get(ToolCredentialRow, credential_id)
        if row is not None:
            row.meta = {"dev_stub": True, "source": "ai_supplier"}
            session.flush()
    else:
        credential_id = credentials[0]["id"]

    for tool in doc.get("tools", []):
        if tool.get("toolId") == "web_client":
            tool["credentialId"] = credential_id

    _seed_agent_draft(service, slug, doc, tool_id="web_client", credential_id=credential_id)

    publication = service.get_latest_publication(slug)
    if publication is not None and publication.body.get("skills"):
        return

    report = validate_agent(service.get_agent_by_slug(slug) or doc)
    if report["errors"] == 0:
        service.publish(slug)
