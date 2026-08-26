from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class AgentRow(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    draft: Mapped["AgentDraftRow | None"] = relationship(back_populates="agent", uselist=False)
    publications: Mapped[list["AgentPublicationRow"]] = relationship(back_populates="agent")


class AgentDraftRow(Base):
    __tablename__ = "agent_drafts"

    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    body: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    agent: Mapped[AgentRow] = relationship(back_populates="draft")


class AgentPublicationRow(Base):
    __tablename__ = "agent_publications"
    __table_args__ = (UniqueConstraint("agent_id", "version", name="uq_agent_publication_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    version: Mapped[str] = mapped_column(String(32))
    body: Mapped[dict] = mapped_column(JSONB)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    agent: Mapped[AgentRow] = relationship(back_populates="publications")


class ToolCatalogRow(Base):
    __tablename__ = "tool_catalog"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    definition: Mapped[dict] = mapped_column(JSONB)


class ToolCredentialRow(Base):
    __tablename__ = "tool_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    tool_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    secret_encrypted: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    agent: Mapped[AgentRow] = relationship()


class SkillRunRow(Base):
    __tablename__ = "skill_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(36), index=True)
    agent_slug: Mapped[str] = mapped_column(String(128), index=True)
    skill_id: Mapped[str] = mapped_column(String(128))
    publication_version: Mapped[str] = mapped_column(String(32))
    current_state: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    vars: Mapped[dict] = mapped_column(JSONB, default=dict)
    history: Mapped[list] = mapped_column(JSONB, default=list)
    conversation_id: Mapped[str | None] = mapped_column(String(256), index=True, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class SkillRunEventRow(Base):
    __tablename__ = "skill_run_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("skill_runs.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    from_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    to_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_calls: Mapped[list] = mapped_column(JSONB, default=list)
    created: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
