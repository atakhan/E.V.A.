from __future__ import annotations

import copy
import re
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from definition.behavior.materialize import flatten_agent_document
from definition.mappers.action_mapper import normalize_action_document
from definition.mappers.skill_mapper import skill_from_document
from definition.system_skills import library_agent_skills, runtime_agent_skills
from definition.validation.validate_agent import validate_agent
from infrastructure.models.tables import (
    AgentDraftRow,
    AgentPublicationRow,
    AgentRow,
    ToolCatalogRow,
    ToolCredentialRow,
)

# Slugs created by integration tests; safe to delete on dev startup.
EPHEMERAL_AGENT_SLUG_PREFIXES = (
    "eva-test-",
    "test-agent-",
    "web-agent-",
    "cred-agent-",
)

_AGENT_KINDS = {"library", "runtime", "fork", "platform"}
EVA_AGENT_SLUG = "eva"


class AgentArchivedError(Exception):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Agent '{slug}' is archived")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_draft_body(agent: AgentRow) -> dict[str, Any]:
    now = _utcnow_iso()
    return {
        "id": agent.id,
        "slug": agent.slug,
        "name": agent.name,
        "description": agent.description,
        "icon": getattr(agent, "icon", "") or "",
        "createdAt": now,
        "updatedAt": now,
        "skills": [],
        "actions": [],
        "tools": [],
        "constructor": {"nodes": []},
        "world": {"addresses": []},
    }


def _merge_agent(agent: AgentRow, draft_body: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": agent.id,
        "slug": agent.slug,
        "name": agent.name,
        "description": agent.description,
        "icon": getattr(agent, "icon", "") or draft_body.get("icon") or "",
        "createdAt": agent.created_at.isoformat(),
        "updatedAt": agent.updated_at.isoformat(),
        "archivedAt": agent.archived_at.isoformat() if agent.archived_at else None,
        "defaultSkillId": draft_body.get("defaultSkillId") or None,
        "skills": draft_body.get("skills", []),
        "actions": draft_body.get("actions", []),
        "tools": draft_body.get("tools", []),
        "constructor": draft_body.get("constructor") or {"nodes": []},
        "world": draft_body.get("world") or {"addresses": []},
        "kind": draft_body.get("kind") if draft_body.get("kind") in _AGENT_KINDS else "library",
        "projectSlug": draft_body.get("projectSlug") or None,
        "originSlug": draft_body.get("originSlug") or None,
    }


def _remap_credential_ids(tools: list[Any], mapping: dict[str, str]) -> list[Any]:
    for tool in tools:
        if isinstance(tool, dict) and tool.get("credentialId") in mapping:
            tool["credentialId"] = mapping[str(tool["credentialId"])]
    return tools


def _remap_world_credentials(world: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    addresses = world.get("addresses")
    if isinstance(addresses, list):
        for address in addresses:
            if isinstance(address, dict) and address.get("credentialId") in mapping:
                address["credentialId"] = mapping[str(address["credentialId"])]
    return world


def _summary_from_row(row: AgentRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "icon": getattr(row, "icon", "") or "",
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
        "archivedAt": row.archived_at.isoformat() if row.archived_at else None,
    }


# What runtime reads from a publication, by part of the agent document.
# Editor layout (constructor nodes, FSM state boxes, viewports) and timestamps are left out.
# World addresses too: ingress reads them from the draft, so they apply without publishing.
_RUNTIME_PARTS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "defaultSkillId": lambda body: body.get("defaultSkillId") or None,
    "skills": lambda body: [skill_from_document(skill).model_dump() for skill in body.get("skills") or []],
    "actions": lambda body: [
        normalize_action_document(action).model_dump() for action in body.get("actions") or []
    ],
    "tools": lambda body: body.get("tools") or [],
}


def changed_runtime_parts(draft: dict[str, Any], published: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for part, project in _RUNTIME_PARTS.items():
        try:
            same = project(draft) == project(published)
        except (AttributeError, KeyError, TypeError, ValueError):
            # Validation refuses to publish what runtime cannot read, so it differs.
            same = False
        if not same:
            changed.append(part)
    return changed


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
        return flatten_agent_document(_merge_agent(agent, agent.draft.body))

    def create_agent(
        self,
        *,
        name: str,
        slug: str,
        description: str = "",
        kind: str = "library",
        project_slug: str | None = None,
        skills: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self.session.scalar(select(AgentRow).where(AgentRow.slug == slug)):
            raise ValueError(f"Slug '{slug}' already exists")

        agent = AgentRow(slug=slug, name=name.strip(), description=description.strip())
        self.session.add(agent)
        self.session.flush()

        now = _utcnow_iso()
        body = _empty_draft_body(agent)
        body["kind"] = kind if kind in _AGENT_KINDS else "library"
        if project_slug:
            body["projectSlug"] = project_slug
        body["skills"] = skills if skills is not None else library_agent_skills(now)
        if tools is not None:
            body["tools"] = tools
        draft = AgentDraftRow(agent_id=agent.id, body=body)
        self.session.add(draft)
        self.session.flush()
        return _merge_agent(agent, body)

    def fork_library_agent(self, origin_slug: str, project_slug: str) -> dict[str, Any]:
        """Copy a library agent into a project. Later edits of either side stay apart."""
        origin = self.get_agent_by_slug(origin_slug)
        if origin is None:
            raise KeyError(f"Agent '{origin_slug}' not found")
        if origin.get("kind") == "fork" and origin.get("originSlug"):
            return self.fork_library_agent(str(origin["originSlug"]), project_slug)
        if origin.get("kind") == "runtime":
            raise ValueError("Системного агента проекта нельзя форкнуть")
        if origin.get("kind") == "platform":
            raise ValueError("Системного агента платформы нельзя форкнуть")
        existing = self._find_fork(origin_slug, project_slug)
        if existing is not None:
            return existing

        slug = self._mint_fork_slug(origin_slug, project_slug)
        agent = AgentRow(
            slug=slug,
            name=str(origin.get("name") or origin_slug),
            description=str(origin.get("description") or ""),
            icon=str(origin.get("icon") or ""),
        )
        self.session.add(agent)
        self.session.flush()
        mapping = self._copy_credentials(str(origin["id"]), agent.id)
        now = _utcnow_iso()
        body = {
            "id": agent.id,
            "slug": slug,
            "name": agent.name,
            "description": agent.description,
            "icon": agent.icon,
            "createdAt": now,
            "updatedAt": now,
            "defaultSkillId": origin.get("defaultSkillId") or None,
            "skills": copy.deepcopy(origin.get("skills") or []),
            "actions": copy.deepcopy(origin.get("actions") or []),
            "tools": _remap_credential_ids(copy.deepcopy(origin.get("tools") or []), mapping),
            "constructor": copy.deepcopy(origin.get("constructor") or {"nodes": []}),
            "world": _remap_world_credentials(copy.deepcopy(origin.get("world") or {"addresses": []}), mapping),
            "kind": "fork",
            "projectSlug": project_slug,
            "originSlug": origin_slug,
        }
        self.session.add(AgentDraftRow(agent_id=agent.id, body=body))
        self.session.flush()
        return _merge_agent(agent, body)

    def _find_fork(self, origin_slug: str, project_slug: str) -> dict[str, Any] | None:
        rows = self.session.scalars(select(AgentRow)).all()
        for row in rows:
            body = row.draft.body if row.draft and isinstance(row.draft.body, dict) else {}
            if (
                body.get("kind") == "fork"
                and body.get("originSlug") == origin_slug
                and body.get("projectSlug") == project_slug
                and row.archived_at is None
            ):
                return self.get_agent_by_slug(row.slug)
        return None

    def _mint_fork_slug(self, origin_slug: str, project_slug: str) -> str:
        raw = re.sub(r"[^a-z0-9-]+", "-", f"{origin_slug}-{project_slug}".lower()).strip("-")[:48].strip("-")
        if len(raw) < 2 or not raw[:1].isalpha():
            raw = f"a-{raw}".strip("-")[:48]
        candidate = raw
        suffix = 2
        while self.session.scalar(select(AgentRow.id).where(AgentRow.slug == candidate)):
            tail = f"-{suffix}"
            candidate = f"{raw[: 48 - len(tail)]}{tail}"
            suffix += 1
        return candidate

    def _copy_credentials(self, origin_id: str, fork_id: str) -> dict[str, str]:
        rows = self.session.scalars(
            select(ToolCredentialRow).where(ToolCredentialRow.agent_id == origin_id)
        ).all()
        mapping: dict[str, str] = {}
        for row in rows:
            copied = str(uuid.uuid4())
            mapping[row.id] = copied
            self.session.add(
                ToolCredentialRow(
                    id=copied,
                    agent_id=fork_id,
                    tool_id=row.tool_id,
                    name=row.name,
                    secret_encrypted=row.secret_encrypted,
                    meta=dict(row.meta or {}),
                )
            )
        self.session.flush()
        return mapping

    def upsert_draft(self, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        agent = self.ensure_active(slug)

        agent.name = str(payload.get("name", agent.name)).strip() or agent.name
        agent.description = str(payload.get("description", agent.description)).strip()
        if "icon" in payload:
            agent.icon = str(payload.get("icon") or "").strip()
        agent.updated_at = datetime.now(timezone.utc)

        if agent.draft is None:
            agent.draft = AgentDraftRow(agent_id=agent.id, body={})

        previous = agent.draft.body if agent.draft and isinstance(agent.draft.body, dict) else {}
        default_skill_id = str(payload.get("defaultSkillId") or "").strip() or None
        kind = payload.get("kind") or previous.get("kind") or "library"
        if kind not in _AGENT_KINDS:
            kind = "library"
        project_slug = payload.get("projectSlug")
        if not project_slug:
            project_slug = previous.get("projectSlug")
        origin_slug = payload.get("originSlug")
        if not origin_slug:
            origin_slug = previous.get("originSlug")
        body = flatten_agent_document({
            "id": agent.id,
            "slug": agent.slug,
            "name": agent.name,
            "description": agent.description,
            "icon": agent.icon,
            "createdAt": agent.created_at.isoformat(),
            "updatedAt": _utcnow_iso(),
            "defaultSkillId": default_skill_id,
            "skills": payload.get("skills", []),
            "actions": payload.get("actions", []),
            "tools": payload.get("tools", []),
            "constructor": payload.get("constructor") or {"nodes": []},
            "world": payload.get("world") or {"addresses": []},
            "kind": kind,
            "projectSlug": project_slug or None,
            "originSlug": origin_slug or None,
        })
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

        body = flatten_agent_document(_merge_agent(agent, agent.draft.body))
        report = validate_agent(body)
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
            body=body,
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

    def draft_changes(self, slug: str) -> list[str] | None:
        """Parts runtime reads that differ between the draft and the latest publication; None before the first one."""
        publication = self.get_latest_publication(slug)
        draft = self.get_agent_by_slug(slug)
        if publication is None or draft is None:
            return None
        return changed_runtime_parts(draft, publication.body)

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


def ensure_eva_agent(session: Session) -> str:
    """Platform agent that runs the projects desk. Hidden from the library."""
    service = AgentService(session)
    existing = service.get_agent_by_slug(EVA_AGENT_SLUG)
    if existing is not None:
        return EVA_AGENT_SLUG
    now = _utcnow_iso()
    service.create_agent(
        name="Ева",
        slug=EVA_AGENT_SLUG,
        description="Системный агент платформы. Ведёт проекты и говорит с человеком.",
        kind="platform",
        skills=runtime_agent_skills(now),
    )
    session.flush()
    return EVA_AGENT_SLUG


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

