from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from definition.services.agent_service import AgentService, seed_foreman_agent, seed_tool_catalog
from infrastructure.db.session import get_engine, get_session_factory, session_scope
from infrastructure.models.tables import Base


def init_db() -> None:
    settings = get_settings()
    engine = get_engine()
    if settings.auto_migrate:
        Base.metadata.create_all(bind=engine)
    with session_scope() as session:
        seed_tool_catalog(session)
        seed_foreman_agent(session)


def get_agent_service(session: Session) -> AgentService:
    return AgentService(session)
