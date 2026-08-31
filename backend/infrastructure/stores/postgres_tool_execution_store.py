from __future__ import annotations

from domain.action_run import ToolExecution, ToolExecutionStatus
from infrastructure.models.tables import ToolExecutionRow
from sqlalchemy import select
from sqlalchemy.orm import Session


class PostgresToolExecutionStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, execution: ToolExecution) -> ToolExecution:
        row = ToolExecutionRow(
            id=execution.id,
            action_run_id=execution.action_run_id,
            tool_instance_id=execution.tool_instance_id,
            command=execution.command,
            input=execution.input,
            output=execution.output,
            status=execution.status.value,
            error=execution.error,
            duration_ms=execution.duration_ms,
            attempt=execution.attempt,
        )
        self.session.add(row)
        self.session.flush()
        return execution

    def update(self, execution: ToolExecution) -> None:
        row = self.session.get(ToolExecutionRow, execution.id)
        if row is None:
            raise KeyError(f"ToolExecution '{execution.id}' not found")
        row.output = execution.output
        row.status = execution.status.value
        row.error = execution.error
        row.duration_ms = execution.duration_ms
        row.attempt = execution.attempt
        self.session.flush()

    def list_for_action_run(self, action_run_id: str) -> list[ToolExecution]:
        rows = self.session.scalars(
            select(ToolExecutionRow).where(ToolExecutionRow.action_run_id == action_run_id)
        ).all()
        return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row: ToolExecutionRow) -> ToolExecution:
        return ToolExecution(
            id=row.id,
            action_run_id=row.action_run_id,
            tool_instance_id=row.tool_instance_id,
            command=row.command,
            input=dict(row.input or {}),
            output=dict(row.output or {}),
            status=ToolExecutionStatus(row.status),
            error=row.error,
            duration_ms=row.duration_ms,
            attempt=row.attempt or 1,
        )
