from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from infrastructure.models.tables import ToolApiLogRow


class ToolApiLogService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(
        self,
        *,
        agent_id: str,
        tool_id: str,
        command: str,
        credential_id: str | None = None,
        model: str | None = None,
        status: str,
        request_summary: dict[str, Any] | None = None,
        response_summary: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
        skill_run_id: str | None = None,
        action_id: str | None = None,
        tool_execution_id: str | None = None,
    ) -> ToolApiLogRow:
        row = ToolApiLogRow(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            credential_id=credential_id,
            tool_id=tool_id,
            command=command,
            model=model,
            status=status,
            request_summary=request_summary or {},
            response_summary=response_summary or {},
            usage=usage or {},
            duration_ms=duration_ms,
            error_message=error_message,
            skill_run_id=skill_run_id,
            action_id=action_id,
            tool_execution_id=tool_execution_id,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_logs(
        self,
        agent_id: str,
        *,
        tool_id: str | None = None,
        credential_id: str | None = None,
        command: str | None = None,
        status: str | None = None,
        skill_run_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        query = select(ToolApiLogRow).where(ToolApiLogRow.agent_id == agent_id)
        if tool_id:
            query = query.where(ToolApiLogRow.tool_id == tool_id)
        if credential_id:
            query = query.where(ToolApiLogRow.credential_id == credential_id)
        if command:
            query = query.where(ToolApiLogRow.command == command)
        if status:
            query = query.where(ToolApiLogRow.status == status)
        if skill_run_id:
            query = query.where(ToolApiLogRow.skill_run_id == skill_run_id)

        safe_limit = max(1, min(limit, 500))
        safe_offset = max(0, offset)

        total = self.session.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0

        rows = self.session.scalars(
            query.order_by(ToolApiLogRow.created_at.desc())
            .offset(safe_offset)
            .limit(safe_limit)
        ).all()

        return {
            "items": [self._public_view(row) for row in rows],
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def stats(
        self,
        agent_id: str,
        *,
        tool_id: str | None = None,
        credential_id: str | None = None,
        skill_run_id: str | None = None,
        hours: int | None = None,
    ) -> dict[str, Any]:
        filters = [ToolApiLogRow.agent_id == agent_id]
        if tool_id:
            filters.append(ToolApiLogRow.tool_id == tool_id)
        if credential_id:
            filters.append(ToolApiLogRow.credential_id == credential_id)
        if skill_run_id:
            filters.append(ToolApiLogRow.skill_run_id == skill_run_id)
        if hours is not None and hours > 0:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)
            filters.append(ToolApiLogRow.created_at >= since)

        total = self.session.scalar(select(func.count()).where(*filters)) or 0
        ok_count = self.session.scalar(
            select(func.count()).where(*filters, ToolApiLogRow.status == "ok")
        ) or 0
        error_count = self.session.scalar(
            select(func.count()).where(*filters, ToolApiLogRow.status == "error")
        ) or 0
        avg_duration = self.session.scalar(
            select(func.avg(ToolApiLogRow.duration_ms)).where(
                *filters,
                ToolApiLogRow.duration_ms.is_not(None),
            )
        )

        by_tool_rows = self.session.execute(
            select(
                ToolApiLogRow.tool_id,
                func.count().label("count"),
                func.avg(ToolApiLogRow.duration_ms).label("avg_ms"),
                func.sum(
                    case((ToolApiLogRow.status == "error", 1), else_=0)
                ).label("errors"),
            )
            .where(*filters)
            .group_by(ToolApiLogRow.tool_id)
            .order_by(func.count().desc())
        ).all()

        by_command_rows = self.session.execute(
            select(
                ToolApiLogRow.tool_id,
                ToolApiLogRow.command,
                func.count().label("count"),
            )
            .where(*filters)
            .group_by(ToolApiLogRow.tool_id, ToolApiLogRow.command)
            .order_by(func.count().desc())
            .limit(12)
        ).all()

        usage_totals: dict[str, int] = {}
        usage_rows = self.session.scalars(
            select(ToolApiLogRow.usage).where(*filters).order_by(ToolApiLogRow.created_at.desc()).limit(500)
        ).all()
        for usage in usage_rows:
            if not isinstance(usage, dict):
                continue
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = usage.get(key)
                if isinstance(value, (int, float)):
                    usage_totals[key] = usage_totals.get(key, 0) + int(value)

        return {
            "total": total,
            "ok": ok_count,
            "error": error_count,
            "avgDurationMs": round(float(avg_duration), 1) if avg_duration is not None else None,
            "byTool": [
                {
                    "toolId": row.tool_id,
                    "count": row.count,
                    "avgDurationMs": round(float(row.avg_ms), 1) if row.avg_ms is not None else None,
                    "errors": int(row.errors or 0),
                }
                for row in by_tool_rows
            ],
            "byCommand": [
                {
                    "toolId": row.tool_id,
                    "command": row.command,
                    "count": row.count,
                }
                for row in by_command_rows
            ],
            "usageTotals": usage_totals,
            "windowHours": hours,
        }

    @staticmethod
    def _public_view(row: ToolApiLogRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "toolId": row.tool_id,
            "credentialId": row.credential_id,
            "command": row.command,
            "model": row.model,
            "status": row.status,
            "requestSummary": row.request_summary or {},
            "responseSummary": row.response_summary or {},
            "usage": row.usage or {},
            "durationMs": row.duration_ms,
            "errorMessage": row.error_message,
            "skillRunId": row.skill_run_id,
            "actionId": row.action_id,
            "toolExecutionId": row.tool_execution_id,
            "createdAt": row.created_at.isoformat(),
        }
