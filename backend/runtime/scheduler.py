from __future__ import annotations

from datetime import datetime, timezone

from definition.mappers.event_mapper import create_domain_event
from domain.events import Event
from infrastructure.models.tables import TimerScheduleRow
from infrastructure.redis.event_bus import publish_event
from sqlalchemy import select
from sqlalchemy.orm import Session


class RuntimeScheduler:
    def __init__(self, session: Session) -> None:
        self.session = session

    def schedule(
        self,
        *,
        run_id: str,
        fire_at: datetime,
        event_type: str = "timer.elapsed",
        payload: dict | None = None,
    ) -> TimerScheduleRow:
        row = TimerScheduleRow(
            run_id=run_id,
            fire_at=fire_at,
            event_type=event_type,
            payload=payload or {},
        )
        self.session.add(row)
        self.session.flush()
        return row

    def process_due(self, *, agent_slug: str, skill_id: str, limit: int = 50) -> int:
        now = datetime.now(timezone.utc)
        rows = self.session.scalars(
            select(TimerScheduleRow)
            .where(TimerScheduleRow.fired.is_(False), TimerScheduleRow.fire_at <= now)
            .order_by(TimerScheduleRow.fire_at.asc())
            .limit(limit)
        ).all()
        count = 0
        for row in rows:
            event: Event = create_domain_event(
                row.event_type,
                source="scheduler",
                payload=dict(row.payload or {}),
                skill_run_id=row.run_id,
            )
            publish_event(event, agent_slug=agent_slug, skill_id=skill_id)
            row.fired = True
            count += 1
        if count:
            self.session.flush()
        return count
