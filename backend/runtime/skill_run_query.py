from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from domain.agent import SkillRunStatus
from infrastructure.models.tables import AgentPublicationRow, AgentRow, SkillRunRow


@dataclass(frozen=True)
class SkillRunListFilters:
    agent_slug: str | None = None
    skill_id: str | None = None
    statuses: tuple[str, ...] = ()
    active_only: bool = False
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class SkillRunListItem:
    skill_run_id: str
    agent_slug: str
    skill_id: str
    status: str
    current_state: str
    publication_version: str
    conversation_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    def to_api(self) -> dict:
        return {
            "skillRunId": self.skill_run_id,
            "agentSlug": self.agent_slug,
            "skillId": self.skill_id,
            "status": self.status,
            "currentState": self.current_state,
            "publicationVersion": self.publication_version,
            "conversationId": self.conversation_id,
            "error": self.error,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
        }


@dataclass
class AgentRunCounts:
    agent_slug: str
    running: int = 0
    waiting: int = 0
    error: int = 0
    completed: int = 0
    cancelled: int = 0
    latest_publication_version: str | None = None
    is_published: bool = False
    archived: bool = False

    def to_api(self) -> dict:
        return {
            "agentSlug": self.agent_slug,
            "running": self.running,
            "waiting": self.waiting,
            "error": self.error,
            "completed": self.completed,
            "cancelled": self.cancelled,
            "latestPublicationVersion": self.latest_publication_version,
            "isPublished": self.is_published,
            "archived": self.archived,
        }


@dataclass
class RuntimeSummaryTotals:
    running: int = 0
    waiting: int = 0
    error: int = 0
    completed_24h: int = 0

    def to_api(self) -> dict:
        return {
            "running": self.running,
            "waiting": self.waiting,
            "error": self.error,
            "completed24h": self.completed_24h,
        }


ACTIVE_STATUSES = (SkillRunStatus.running.value, SkillRunStatus.waiting.value)


def row_to_list_item(row: SkillRunRow) -> SkillRunListItem:
    return SkillRunListItem(
        skill_run_id=row.id,
        agent_slug=row.agent_slug,
        skill_id=row.skill_id,
        status=row.status,
        current_state=row.current_state,
        publication_version=row.publication_version,
        conversation_id=row.conversation_id,
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def run_detail_from_row(row: SkillRunRow) -> dict:
    return {
        "ok": True,
        "created": False,
        "skillRunId": row.id,
        "agentSlug": row.agent_slug,
        "skillId": row.skill_id,
        "status": row.status,
        "currentState": row.current_state,
        "publicationVersion": row.publication_version,
        "conversationId": row.conversation_id,
        "error": row.error,
        "history": list(row.history or []),
        "toolCalls": [],
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }


def completed_since_24h() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=24)
