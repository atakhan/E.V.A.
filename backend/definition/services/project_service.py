from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from definition.interaction_manifest import ensure_agents_channel
from tools.pulse import ensure_pulse_tool
from definition.services.agent_service import EVA_AGENT_SLUG, AgentService, ensure_eva_agent
from definition.system_skills import runtime_agent_skills
from infrastructure.models.tables import AgentRow, ProjectRow

_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_RESERVED = {"projects", "agents", "runtime", "tools", "api", "health", "applications", "eva"}


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _normalize_agents(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    agents: list[dict[str, Any]] = []
    for item in raw:
        slug = str(item.get("agentSlug") or item.get("agent_slug") or "").strip()
        if not slug or slug in seen:
            raise ValueError("У проекта не может быть двух одинаковых агентов")
        seen.add(slug)
        agents.append(
            {
                "agentSlug": slug,
                **({"originSlug": origin} if (origin := str(item.get("originSlug") or "").strip()) else {}),
                "x": float(item.get("x") or 0),
                "y": float(item.get("y") or 0),
            }
        )
    return agents


def _project_channel_instance() -> dict[str, Any]:
    return {
        "id": "project",
        "toolId": "project",
        "name": "Проект",
        "enabled": True,
        "config": {},
    }


def _runtime_slug(project_slug: str) -> str:
    raw = re.sub(r"[^a-z0-9-]+", "-", f"rt-{project_slug.lower()}").strip("-")[:48].strip("-")
    if len(raw) < 2 or not raw[0].isalpha():
        raw = f"rt-{project_slug.lower()}"[:48].strip("-")
    return raw


def _to_api(row: ProjectRow, runtime_agent_slug: str | None = None) -> dict[str, Any]:
    return {
        "id": row.id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description or "",
        "agents": list(row.agents or []),
        "runtimeAgentSlug": runtime_agent_slug,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


class ProjectService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _find_runtime(self, project_slug: str) -> AgentRow | None:
        matches: list[AgentRow] = []
        rows = self._session.scalars(select(AgentRow)).all()
        for row in rows:
            body = row.draft.body if row.draft is not None else {}
            if (
                isinstance(body, dict)
                and body.get("kind") == "runtime"
                and body.get("projectSlug") == project_slug
            ):
                matches.append(row)
        preferred = _runtime_slug(project_slug)
        for row in matches:
            if row.slug == preferred:
                return row
        return matches[0] if matches else None

    def _project_name(self, project_slug: str) -> str:
        row = self._session.scalar(select(ProjectRow).where(ProjectRow.slug == project_slug))
        return (row.name if row is not None else "") or project_slug

    def _sync_runtime_name(self, row: AgentRow, project_slug: str) -> None:
        name = self._project_name(project_slug).strip()
        if not name or row.name == name:
            return
        row.name = name

    def ensure_runtime_agent(self, project_slug: str) -> str:
        found = self._find_runtime(project_slug)
        if found is not None:
            self._ensure_project_channel(found)
            self._sync_runtime_name(found, project_slug)
            self._link_eva_to_runtime(found.slug, found.name)
            return found.slug
        agents = AgentService(self._session)
        slug = _runtime_slug(project_slug)
        existing = agents.get_agent_row(slug)
        if existing is not None:
            found = self._find_runtime(project_slug)
            if found is not None:
                self._sync_runtime_name(found, project_slug)
                self._link_eva_to_runtime(found.slug, found.name)
                return found.slug
            slug = f"{slug[:40].rstrip('-')}-{uuid.uuid4().hex[:4]}"
        now = datetime.now(timezone.utc).isoformat()
        created = agents.create_agent(
            name=self._project_name(project_slug),
            slug=slug,
            description="Системный агент проекта. Собирает работу агентов на столе и говорит с человеком.",
            kind="runtime",
            project_slug=project_slug,
            skills=runtime_agent_skills(now),
            tools=[_project_channel_instance()],
        )
        runtime_slug = str(created.get("slug") or slug)
        self._link_eva_to_runtime(runtime_slug, str(created.get("name") or runtime_slug))
        return runtime_slug

    def _link_eva_to_runtime(self, runtime_slug: str, runtime_name: str) -> None:
        """Default Agents-channel wire: Eva ↔ project runtime."""
        ensure_eva_agent(self._session)
        agents = AgentService(self._session)
        eva = agents.get_agent_by_slug(EVA_AGENT_SLUG)
        peers = []
        if eva and isinstance(eva.get("memory"), dict):
            interaction = eva["memory"].get("interaction")
            if isinstance(interaction, dict):
                peers = interaction.get("peers") or []
        if any(isinstance(item, dict) and item.get("agentSlug") == runtime_slug for item in peers):
            return
        agents.link_agents(
            EVA_AGENT_SLUG,
            runtime_slug,
            left_name="Ева",
            right_name=runtime_name or runtime_slug,
        )

    def _ensure_project_channel(self, row: AgentRow) -> None:
        if row.draft is None or not isinstance(row.draft.body, dict):
            return
        body = dict(row.draft.body)
        tools = [item for item in (body.get("tools") or []) if isinstance(item, dict)]
        changed = False
        if not any(item.get("toolId") == "project" for item in tools):
            tools.append(_project_channel_instance())
            body["tools"] = tools
            changed = True
        before = body.get("tools")
        ensure_agents_channel(body)
        ensure_pulse_tool(body)
        if body.get("tools") != before:
            changed = True
        if not changed:
            return
        row.draft.body = body
        row.draft.updated_at = datetime.now(timezone.utc)

    def _ensure_forks(self, row: ProjectRow) -> None:
        current = list(row.agents or [])
        if not current:
            return
        bound = self._bind_agents(row.slug, current, previous=current)
        if bound != current:
            row.agents = bound
            row.updated_at = datetime.now(timezone.utc)
            self._session.flush()

    def _bind_agents(
        self,
        project_slug: str,
        requested: list[dict[str, Any]],
        *,
        previous: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Each library agent placed on a project becomes that project's own copy."""
        agents = AgentService(self._session)
        bound: list[dict[str, Any]] = []
        kept: set[str] = set()
        for item in requested:
            slug = str(item.get("agentSlug") or "")
            doc = agents.get_agent_by_slug(slug)
            point = {"x": float(item.get("x") or 0), "y": float(item.get("y") or 0)}
            if doc is None:
                bound.append({"agentSlug": slug, **point})
                continue
            if doc.get("kind") == "runtime":
                continue
            if doc.get("kind") == "fork" and doc.get("projectSlug") == project_slug:
                origin = str(doc.get("originSlug") or "")
                bound.append({"agentSlug": slug, **({"originSlug": origin} if origin else {}), **point})
                kept.add(slug)
                continue
            origin_slug = str(doc.get("originSlug") or slug)
            if doc.get("kind") == "fork":
                origin_doc = agents.get_agent_by_slug(origin_slug)
                if origin_doc is None:
                    bound.append({"agentSlug": slug, **point})
                    continue
            fork = agents.fork_library_agent(origin_slug, project_slug)
            origin = str(fork.get("originSlug") or origin_slug)
            bound.append(
                {
                    "agentSlug": fork["slug"],
                    "originSlug": origin,
                    **point,
                }
            )
            kept.add(fork["slug"])
        previous_slugs = {str(item.get("agentSlug") or "") for item in previous}
        for old_slug in previous_slugs - kept:
            old = agents.get_agent_by_slug(old_slug)
            if old and old.get("kind") == "fork" and old.get("projectSlug") == project_slug:
                agents.delete_agent(old_slug)
        return bound

    def list_projects(self) -> list[dict[str, Any]]:
        rows = self._session.scalars(select(ProjectRow).order_by(ProjectRow.updated_at.desc())).all()
        result: list[dict[str, Any]] = []
        for row in rows:
            found = self._find_runtime(row.slug)
            result.append(_to_api(row, found.slug if found else None))
        return result

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        row = self._session.scalar(select(ProjectRow).where(ProjectRow.slug == slug))
        if row is None:
            return None
        self._ensure_forks(row)
        return _to_api(row, self.ensure_runtime_agent(slug))

    def create_project(self, *, name: str, slug: str, description: str = "") -> dict[str, Any]:
        cleaned_name = name.strip()
        cleaned_slug = slug.strip().lower()
        if not cleaned_name:
            raise ValueError("Укажите название проекта")
        if not _SLUG_RE.match(cleaned_slug) or cleaned_slug in _RESERVED or len(cleaned_slug) < 2:
            raise ValueError("Некорректный адрес проекта")
        if self._session.scalar(select(ProjectRow.id).where(ProjectRow.slug == cleaned_slug)):
            raise ValueError("Проект с таким адресом уже есть")
        now = datetime.now(timezone.utc)
        row = ProjectRow(
            id=str(uuid.uuid4()),
            slug=cleaned_slug,
            name=cleaned_name,
            description=description.strip(),
            agents=[],
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        runtime_slug = self.ensure_runtime_agent(cleaned_slug)
        return _to_api(row, runtime_slug)

    def update_project(
        self,
        slug: str,
        *,
        name: str | None = None,
        description: str | None = None,
        agents: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        row = self._session.scalar(select(ProjectRow).where(ProjectRow.slug == slug))
        if row is None:
            raise KeyError(slug)
        if name is not None:
            cleaned = name.strip()
            if not cleaned:
                raise ValueError("Укажите название проекта")
            row.name = cleaned
        if description is not None:
            row.description = description.strip()
        if agents is not None:
            row.agents = self._bind_agents(slug, _normalize_agents(agents), previous=list(row.agents or []))
        row.updated_at = datetime.now(timezone.utc)
        self._session.flush()
        found = self._find_runtime(slug)
        if found is not None:
            self._sync_runtime_name(found, slug)
            self._session.flush()
        return _to_api(row, found.slug if found else None)

    def delete_project(self, slug: str) -> None:
        row = self._session.scalar(select(ProjectRow).where(ProjectRow.slug == slug))
        if row is None:
            raise KeyError(slug)
        runtime = self._find_runtime(slug)
        if runtime is not None:
            self._session.delete(runtime)
        for fork_slug in [item.get("agentSlug") for item in list(row.agents or [])]:
            if not fork_slug:
                continue
            fork = AgentService(self._session).get_agent_row(str(fork_slug))
            if fork is None or fork.draft is None or not isinstance(fork.draft.body, dict):
                continue
            body = fork.draft.body
            if body.get("kind") == "fork" and body.get("projectSlug") == slug:
                self._session.delete(fork)
        self._session.delete(row)
        self._session.flush()
