from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.agent import SkillRun, SkillRunStatus
from infrastructure.models.tables import SkillRunEventRow, SkillRunRow
from runtime.stores.skill_run_store import SkillRunStore


class PostgresSkillRunStore(SkillRunStore):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_run(self, run_id: str) -> SkillRun | None:
        row = self.session.get(SkillRunRow, run_id)
        if row is None:
            return None
        return self._to_domain(row)

    def save_run(self, run: SkillRun) -> None:
        row = self.session.get(SkillRunRow, run.id)
        if row is None:
            row = SkillRunRow(
                id=run.id,
                agent_id=run.vars.get("_agent_id", ""),
                agent_slug=run.vars.get("_agent_slug", ""),
                skill_id=run.skill_id,
                publication_version=run.skill_version,
                current_state=run.current_state,
                status=run.status.value,
                vars=run.vars,
                history=run.history,
                conversation_id=run.vars.get("conversation_id"),
                error=run.error,
            )
            self.session.add(row)
        else:
            row.current_state = run.current_state
            row.status = run.status.value
            row.vars = run.vars
            row.history = run.history
            row.conversation_id = run.vars.get("conversation_id")
            row.error = run.error
        self.session.flush()

    def find_waiting_by_conversation(self, conversation_id: str) -> SkillRun | None:
        row = self.session.scalar(
            select(SkillRunRow)
            .where(
                SkillRunRow.conversation_id == conversation_id,
                SkillRunRow.status.in_([SkillRunStatus.waiting.value, SkillRunStatus.running.value]),
            )
            .order_by(SkillRunRow.updated_at.desc())
            .limit(1)
        )
        return self._to_domain(row) if row else None

    def map_conversation(self, conversation_id: str, run_id: str) -> None:
        row = self.session.get(SkillRunRow, run_id)
        if row is not None:
            row.conversation_id = conversation_id
            self.session.flush()

    def append_event_log(
        self,
        *,
        run_id: str,
        event_type: str,
        payload: dict,
        from_state: str | None,
        to_state: str | None,
        tool_calls: list,
        created: bool,
    ) -> None:
        self.session.add(
            SkillRunEventRow(
                run_id=run_id,
                event_type=event_type,
                payload=payload,
                from_state=from_state,
                to_state=to_state,
                tool_calls=tool_calls,
                created=created,
            )
        )
        self.session.flush()

    @staticmethod
    def _to_domain(row: SkillRunRow) -> SkillRun:
        return SkillRun(
            id=row.id,
            skill_id=row.skill_id,
            skill_version=row.publication_version,
            current_state=row.current_state,
            status=SkillRunStatus(row.status),
            vars=dict(row.vars or {}),
            history=list(row.history or []),
            error=row.error,
        )
