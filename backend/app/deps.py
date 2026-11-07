from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from definition.services.agent_service import (
    AgentService,
    ensure_eva_agent,
    ensure_life_skill_on_agents,
    prune_ephemeral_agents,
    seed_tool_catalog,
)
from definition.services.auth_service import AuthService
from infrastructure.db.session import get_engine, session_scope
from infrastructure.models.tables import Base, UserRow

# Re-export for API modules that import session_scope from app.deps.
__all__ = [
    "db_session",
    "get_agent_service",
    "init_db",
    "require_user",
    "session_scope",
]


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
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS icon TEXT DEFAULT ''",
        "ALTER TABLE agents ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(36)",
        "CREATE INDEX IF NOT EXISTS ix_agents_archived_at ON agents (archived_at)",
        "CREATE INDEX IF NOT EXISTS ix_agents_owner_user_id ON agents (owner_user_id)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _ensure_project_schema(engine) -> None:
    from sqlalchemy import text

    statements = [
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(36)",
        "CREATE INDEX IF NOT EXISTS ix_projects_owner_user_id ON projects (owner_user_id)",
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
        _ensure_project_schema(engine)
        _ensure_runtime_schema(engine)
    with session_scope() as session:
        seed_tool_catalog(session)
        ensure_eva_agent(session)
        ensure_life_skill_on_agents(session)
        auth = AuthService(session)
        admin = auth.ensure_bootstrap_admin()
        auth.assign_orphan_ownership(admin)
        if settings.prune_ephemeral_agents:
            prune_ephemeral_agents(session)


def get_agent_service(session: Session) -> AgentService:
    return AgentService(session)


def db_session() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session


def require_user(request: Request, session: Session = Depends(db_session)) -> UserRow:
    settings = get_settings()
    user = AuthService(session).resolve_session(request.cookies.get(settings.auth_cookie_name))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
