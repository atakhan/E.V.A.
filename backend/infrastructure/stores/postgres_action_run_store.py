from __future__ import annotations

from datetime import datetime, timezone

from domain.action_run import ActionRun, ActionRunStatus
from infrastructure.models.tables import ActionRunRow
from sqlalchemy import select
from sqlalchemy.orm import Session


class PostgresActionRunStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, action_run: ActionRun) -> ActionRun:
        row = ActionRunRow(
            id=action_run.id,
            skill_run_id=action_run.skill_run_id,
            action_id=action_run.action_id,
            action_version=action_run.action_version,
            status=action_run.status.value,
            input=action_run.input,
            output=action_run.output,
            current_step=action_run.current_step,
            error=action_run.error,
            attempt=action_run.attempt,
            deadline_at=action_run.deadline_at,
            started_at=action_run.started_at,
            finished_at=action_run.finished_at,
        )
        self.session.add(row)
        self.session.flush()
        return action_run

    def update(self, action_run: ActionRun) -> None:
        row = self.session.get(ActionRunRow, action_run.id)
        if row is None:
            raise KeyError(f"ActionRun '{action_run.id}' not found")
        row.status = action_run.status.value
        row.output = action_run.output
        row.current_step = action_run.current_step
        row.error = action_run.error
        row.attempt = action_run.attempt
        row.deadline_at = action_run.deadline_at
        row.started_at = action_run.started_at
        row.finished_at = action_run.finished_at
        self.session.flush()

    def get(self, action_run_id: str) -> ActionRun | None:
        row = self.session.get(ActionRunRow, action_run_id)
        return self._to_domain(row) if row else None

    def list_for_run(self, skill_run_id: str) -> list[ActionRun]:
        rows = self.session.scalars(
            select(ActionRunRow).where(ActionRunRow.skill_run_id == skill_run_id)
        ).all()
        return [self._to_domain(row) for row in rows]

    def cancel_active_for_run(self, skill_run_id: str) -> None:
        rows = self.session.scalars(
            select(ActionRunRow).where(
                ActionRunRow.skill_run_id == skill_run_id,
                ActionRunRow.status.in_(
                    [ActionRunStatus.created.value, ActionRunStatus.running.value, ActionRunStatus.waiting.value]
                ),
            )
        ).all()
        now = datetime.now(timezone.utc)
        for row in rows:
            row.status = ActionRunStatus.cancelled.value
            row.finished_at = now
        self.session.flush()

    @staticmethod
    def _to_domain(row: ActionRunRow) -> ActionRun:
        return ActionRun(
            id=row.id,
            action_id=row.action_id,
            action_version=row.action_version,
            skill_run_id=row.skill_run_id,
            status=ActionRunStatus(row.status),
            input=dict(row.input or {}),
            output=dict(row.output or {}),
            current_step=row.current_step or "",
            error=row.error,
            attempt=row.attempt or 0,
            deadline_at=row.deadline_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )
