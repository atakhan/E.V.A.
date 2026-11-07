from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from pwdlib import PasswordHash
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from definition.services.agent_service import EVA_AGENT_SLUG
from infrastructure.models.tables import AgentRow, AuthSessionRow, ProjectRow, UserRow

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_password_hash = PasswordHash.recommended()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def user_to_api(user: UserRow) -> dict[str, Any]:
    return {"id": user.id, "email": user.email}


class AuthService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_user_by_email(self, email: str) -> UserRow | None:
        return self._session.scalar(select(UserRow).where(UserRow.email == normalize_email(email)))

    def get_user_by_id(self, user_id: str) -> UserRow | None:
        return self._session.scalar(select(UserRow).where(UserRow.id == user_id))

    def register(self, *, email: str, password: str) -> UserRow:
        settings = get_settings()
        if not settings.auth_open_registration:
            raise PermissionError("Registration is closed")
        cleaned = normalize_email(email)
        if not cleaned or not _EMAIL_RE.match(cleaned):
            raise ValueError("Invalid email")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if self.get_user_by_email(cleaned) is not None:
            raise ValueError("Email already registered")
        user = UserRow(email=cleaned, password_hash=hash_password(password))
        self._session.add(user)
        self._session.flush()
        return user

    def authenticate(self, *, email: str, password: str) -> UserRow:
        user = self.get_user_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise PermissionError("Invalid email or password")
        return user

    def create_session(self, user: UserRow) -> AuthSessionRow:
        settings = get_settings()
        session = AuthSessionRow(
            id=secrets.token_urlsafe(32),
            user_id=user.id,
            expires_at=_utcnow() + timedelta(hours=settings.auth_session_ttl_hours),
        )
        self._session.add(session)
        self._session.flush()
        return session

    def resolve_session(self, session_id: str | None) -> UserRow | None:
        if not session_id:
            return None
        row = self._session.scalar(select(AuthSessionRow).where(AuthSessionRow.id == session_id))
        if row is None or row.revoked_at is not None:
            return None
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= _utcnow():
            return None
        return self.get_user_by_id(row.user_id)

    def revoke_session(self, session_id: str | None) -> None:
        if not session_id:
            return
        row = self._session.scalar(select(AuthSessionRow).where(AuthSessionRow.id == session_id))
        if row is None or row.revoked_at is not None:
            return
        row.revoked_at = _utcnow()
        self._session.flush()

    def ensure_bootstrap_admin(self) -> UserRow:
        settings = get_settings()
        email = normalize_email(settings.bootstrap_admin_email)
        existing = self.get_user_by_email(email)
        if existing is not None:
            return existing
        user = UserRow(
            email=email,
            password_hash=hash_password(settings.bootstrap_admin_password),
        )
        self._session.add(user)
        self._session.flush()
        return user

    def assign_orphan_ownership(self, owner: UserRow) -> None:
        """Give bootstrap admin any projects/agents that still lack an owner (except system eva)."""
        projects = self._session.scalars(
            select(ProjectRow).where(
                or_(ProjectRow.owner_user_id.is_(None), ProjectRow.owner_user_id == "")
            )
        ).all()
        for row in projects:
            row.owner_user_id = owner.id

        agents = self._session.scalars(
            select(AgentRow).where(
                or_(AgentRow.owner_user_id.is_(None), AgentRow.owner_user_id == ""),
                AgentRow.slug != EVA_AGENT_SLUG,
            )
        ).all()
        for row in agents:
            row.owner_user_id = owner.id

        eva = self._session.scalar(select(AgentRow).where(AgentRow.slug == EVA_AGENT_SLUG))
        if eva is not None and eva.owner_user_id is not None:
            eva.owner_user_id = None

        self._session.flush()
