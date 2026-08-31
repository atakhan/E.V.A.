from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.agent import SkillRun, SkillRunStatus
from infrastructure.models.tables import AgentPublicationRow, AgentRow, SkillRunEventRow, SkillRunRow
from runtime.exceptions import ConcurrentUpdateError
from runtime.skill_run_query import (
    ACTIVE_STATUSES,
    AgentRunCounts,
    RuntimeSummaryTotals,
    SkillRunListFilters,
    SkillRunListItem,
    completed_since_24h,
    row_to_list_item,
)
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

    def cancel_active_runs_for_agent(self, agent_slug: str) -> int:
        from infrastructure.stores.postgres_action_run_store import PostgresActionRunStore

        rows = self.session.scalars(
            select(SkillRunRow).where(
                SkillRunRow.agent_slug == agent_slug,
                SkillRunRow.status.in_(ACTIVE_STATUSES),
            )
        ).all()
        if not rows:
            return 0

        action_store = PostgresActionRunStore(self.session)
        for row in rows:
            row.status = SkillRunStatus.cancelled.value
            row.error = None
            action_store.cancel_active_for_run(row.id)
        self.session.flush()
        return len(rows)

    def list_runs(self, filters: SkillRunListFilters) -> tuple[list[SkillRunListItem], int]:
        query = select(SkillRunRow)
        count_query = select(func.count()).select_from(SkillRunRow)

        if filters.agent_slug:
            query = query.where(SkillRunRow.agent_slug == filters.agent_slug)
            count_query = count_query.where(SkillRunRow.agent_slug == filters.agent_slug)

        if filters.skill_id:
            query = query.where(SkillRunRow.skill_id == filters.skill_id)
            count_query = count_query.where(SkillRunRow.skill_id == filters.skill_id)

        if filters.active_only:
            query = query.where(SkillRunRow.status.in_(ACTIVE_STATUSES))
            count_query = count_query.where(SkillRunRow.status.in_(ACTIVE_STATUSES))
        elif filters.statuses:
            query = query.where(SkillRunRow.status.in_(filters.statuses))
            count_query = count_query.where(SkillRunRow.status.in_(filters.statuses))

        total = int(self.session.scalar(count_query) or 0)
        rows = self.session.scalars(
            query.order_by(SkillRunRow.updated_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
        ).all()
        return [row_to_list_item(row) for row in rows], total

    def summarize_runtime(self) -> tuple[list[AgentRunCounts], RuntimeSummaryTotals]:
        active_slugs = set(
            self.session.scalars(
                select(AgentRow.slug).where(AgentRow.archived_at.is_(None))
            ).all()
        )

        status_rows = self.session.execute(
            select(SkillRunRow.agent_slug, SkillRunRow.status, func.count())
            .group_by(SkillRunRow.agent_slug, SkillRunRow.status)
        ).all()

        agents: dict[str, AgentRunCounts] = {}
        totals = RuntimeSummaryTotals()

        for agent_slug, status, count in status_rows:
            if agent_slug not in active_slugs:
                continue
            entry = agents.setdefault(agent_slug, AgentRunCounts(agent_slug=agent_slug))
            if status == SkillRunStatus.running.value:
                entry.running = count
                totals.running += count
            elif status == SkillRunStatus.waiting.value:
                entry.waiting = count
                totals.waiting += count
            elif status == SkillRunStatus.error.value:
                entry.error = count
                totals.error += count
            elif status == SkillRunStatus.completed.value:
                entry.completed = count
            elif status == SkillRunStatus.cancelled.value:
                entry.cancelled = count

        if active_slugs:
            completed_24h = self.session.scalar(
                select(func.count())
                .select_from(SkillRunRow)
                .where(
                    SkillRunRow.status == SkillRunStatus.completed.value,
                    SkillRunRow.updated_at >= completed_since_24h(),
                    SkillRunRow.agent_slug.in_(active_slugs),
                )
            )
        else:
            completed_24h = 0
        totals.completed_24h = int(completed_24h or 0)

        latest_pubs = self.session.execute(
            select(AgentRow.slug, AgentPublicationRow.version)
            .join(AgentPublicationRow, AgentPublicationRow.agent_id == AgentRow.id)
            .order_by(AgentPublicationRow.published_at.desc())
        ).all()
        latest_by_slug: dict[str, str] = {}
        for slug, version in latest_pubs:
            if slug not in active_slugs:
                continue
            if slug not in latest_by_slug:
                latest_by_slug[slug] = version

        for slug in set(agents.keys()) | set(latest_by_slug.keys()):
            entry = agents.setdefault(slug, AgentRunCounts(agent_slug=slug))
            entry.latest_publication_version = latest_by_slug.get(slug)
            entry.is_published = slug in latest_by_slug

        return sorted(agents.values(), key=lambda item: item.agent_slug), totals

    def summarize_agent(self, agent_slug: str) -> AgentRunCounts | None:
        agent = self.session.scalar(select(AgentRow).where(AgentRow.slug == agent_slug))
        if agent is None:
            return None

        status_rows = self.session.execute(
            select(SkillRunRow.status, func.count())
            .where(SkillRunRow.agent_slug == agent_slug)
            .group_by(SkillRunRow.status)
        ).all()

        entry = AgentRunCounts(agent_slug=agent_slug, archived=agent.archived_at is not None)
        for status, count in status_rows:
            if status == SkillRunStatus.running.value:
                entry.running = count
            elif status == SkillRunStatus.waiting.value:
                entry.waiting = count
            elif status == SkillRunStatus.error.value:
                entry.error = count
            elif status == SkillRunStatus.completed.value:
                entry.completed = count
            elif status == SkillRunStatus.cancelled.value:
                entry.cancelled = count

        latest = self.session.scalar(
            select(AgentPublicationRow.version)
            .join(AgentRow, AgentRow.id == AgentPublicationRow.agent_id)
            .where(AgentRow.slug == agent_slug)
            .order_by(AgentPublicationRow.published_at.desc())
            .limit(1)
        )
        entry.latest_publication_version = latest
        entry.is_published = latest is not None
        return entry

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
