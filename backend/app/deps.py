from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from definition.services.agent_service import (
    AgentService,
    prune_ephemeral_agents,
    seed_tool_catalog,
)
from infrastructure.db.session import get_engine, get_session_factory, session_scope
from infrastructure.models.tables import Base


def _ensure_tool_log_schema(engine) -> None:
    from sqlalchemy import text

    statements = [
        "ALTER TABLE tool_api_logs ADD COLUMN IF NOT EXISTS skill_run_id VARCHAR(36)",
        "ALTER TABLE tool_api_logs ADD COLUMN IF NOT EXISTS action_id VARCHAR(128)",
        "CREATE INDEX IF NOT EXISTS ix_tool_api_logs_skill_run_id ON tool_api_logs (skill_run_id)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _ensure_agent_schema(engine) -> None:
    from sqlalchemy import text

    statements = [
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ",
        "CREATE INDEX IF NOT EXISTS ix_agents_archived_at ON agents (archived_at)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _ensure_runtime_schema(engine) -> None:
    from sqlalchemy import text

    statements = [
        "ALTER TABLE skill_runs ADD COLUMN IF NOT EXISTS revision INTEGER DEFAULT 0",
        "ALTER TABLE skill_runs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ",
        "ALTER TABLE tool_api_logs ADD COLUMN IF NOT EXISTS tool_execution_id VARCHAR(36)",
        "CREATE INDEX IF NOT EXISTS ix_tool_api_logs_tool_execution_id ON tool_api_logs (tool_execution_id)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def init_db() -> None:
    settings = get_settings()
    engine = get_engine()
    if settings.auto_migrate:
        Base.metadata.create_all(bind=engine)
        _ensure_tool_log_schema(engine)
        _ensure_agent_schema(engine)
        _ensure_runtime_schema(engine)
    with session_scope() as session:
        seed_tool_catalog(session)
        if settings.prune_ephemeral_agents:
            prune_ephemeral_agents(session)


def get_agent_service(session: Session) -> AgentService:
    return AgentService(session)
