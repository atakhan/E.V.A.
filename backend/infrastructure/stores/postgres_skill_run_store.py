from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.agent import SkillRun, SkillRunStatus
from infrastructure.models.tables import SkillRunEventRow, SkillRunRow
from runtime.exceptions import ConcurrentUpdateError
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
        vars_data = dict(run.vars)
        vars_data["_skill_params"] = dict(run.params)
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
                vars=vars_data,
                history=run.history,
                conversation_id=run.vars.get("conversation_id") or run.params.get("conversation_id"),
                error=run.error,
                revision=run.revision,
                expires_at=_parse_expires(run.expires_at),
            )
            self.session.add(row)
            run.revision = 0
        else:
            expected = run.revision
            if row.revision != expected:
                raise ConcurrentUpdateError(run.id, expected)
            row.current_state = run.current_state
            row.status = run.status.value
            row.vars = vars_data
            row.history = run.history
            row.conversation_id = run.vars.get("conversation_id") or run.params.get("conversation_id")
            row.error = run.error
            row.revision = expected + 1
            row.expires_at = _parse_expires(run.expires_at)
            run.revision = expected + 1
        self.session.flush()

    def find_waiting_by_conversation(self, conversation_id: str) -> SkillRun | None:
        runs = self.find_waiting_runs("conversation_id", conversation_id)
        return runs[0] if runs else None

    def find_waiting_runs(self, correlation_key: str, value: str) -> list[SkillRun]:
        if correlation_key == "conversation_id":
            rows = self.session.scalars(
                select(SkillRunRow)
                .where(
                    SkillRunRow.conversation_id == value,
                    SkillRunRow.status.in_([SkillRunStatus.waiting.value, SkillRunStatus.running.value]),
                )
                .order_by(SkillRunRow.updated_at.desc())
            ).all()
            return [self._to_domain(row) for row in rows]

        rows = self.session.scalars(
            select(SkillRunRow).where(
                SkillRunRow.status.in_([SkillRunStatus.waiting.value, SkillRunStatus.running.value]),
            )
        ).all()
        matches: list[SkillRun] = []
        for row in rows:
            domain = self._to_domain(row)
            if domain.params.get(correlation_key) == value or domain.vars.get(correlation_key) == value:
                matches.append(domain)
        return matches

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

    def list_event_logs(self, run_id: str) -> list[SkillRunEventRow]:
        return list(
            self.session.scalars(
                select(SkillRunEventRow)
                .where(SkillRunEventRow.run_id == run_id)
                .order_by(SkillRunEventRow.created_at.asc())
            ).all()
        )

    @staticmethod
    def _to_domain(row: SkillRunRow) -> SkillRun:
        vars_data = dict(row.vars or {})
        params = vars_data.pop("_skill_params", {})
        if not isinstance(params, dict):
            params = {}
        expires = row.expires_at.isoformat() if row.expires_at else None
        return SkillRun(
            id=row.id,
            skill_id=row.skill_id,
            skill_version=row.publication_version,
            current_state=row.current_state,
            status=SkillRunStatus(row.status),
            params=dict(params),
            vars=vars_data,
            history=list(row.history or []),
            error=row.error,
            revision=row.revision or 0,
            expires_at=expires,
        )


def _parse_expires(value: str | None):
    if not value:
        return None
    from datetime import datetime

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
