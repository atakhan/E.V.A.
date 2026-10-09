# Runtime Implementation Status

> Статус соответствия кода [`RUNTIME_SPEC_v0.1.md`](./RUNTIME_SPEC_v0.1.md).  
> Обновлено: 2026-09-06.  
> Оценка: **~88%** — P0–P2 закрыты; cockpit UI v1; P3 (replay UI, pause) частично. Interaction фаза 1: pin по event.type.

## Summary

| Категория | Оценка |
|-----------|--------|
| Core execution loop | Solid |
| Durable SkillRun + worker | Solid |
| FSM + guards + on_enter | Solid |
| Action recipe + tool instances | Solid |
| Version pinning per run | **Done** |
| ActionRun / ToolExecution entities | **Done** |
| Cancel / retry / timeout | **Partial–Done** |
| Full execution history + observability | **Partial–Done** |
| Runtime Cockpit UI | **Done (v1)** |

**Production path:**

```text
Channel / API → Redis (eva:events) → runtime_worker
  → runtime_factory (pinned publication)
  → RuntimeService.route_all() → SkillRunner → FSMEngine
  → ActionExecutor → ActionRun / ToolExecution stores
  → ToolExecutor → Postgres
```

**Sync / test path:** `POST /api/runtime/runs`, `POST /api/runtime/runs/start`, `EventRouter`, foreman demo.

---

## Acceptance Criteria (§48)

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Start Skill | ✅ | `POST /api/runtime/runs`, `/runs/start` |
| 2 | Persist SkillRun | ✅ | `skill_runs` + `revision` |
| 3 | Interpret FSM | ✅ | `runtime/fsm_engine.py` |
| 4 | Accept Events | ✅ | API, Telegram, Web, Redis worker |
| 5 | Execute Actions | ✅ | `runtime/action_executor.py` |
| 6 | Execute Tool commands | ✅ | `runtime/tool_executor.py` |
| 7 | Persist Action/Tool executions | ✅ | `action_runs`, `tool_executions`, `tool_api_logs` |
| 8 | Suspend Skill | ⚠️ | `waiting`; no `CREATED` enum |
| 9 | Resume Skill on Event | ✅ | Pinned publication on resume |
| 10 | Survive restart | ✅ | Durable runs + stateless worker |
| 11 | Prevent duplicate event processing | ✅ | Dedup + optimistic `revision` + correlation lock |
| 12 | Parallel Skill Runs | ✅ | `route_all` fan-out |
| 13 | Retry | ⚠️ | Tool/action retry config; no skill-level auto-retry |
| 14 | Timeout | ⚠️ | ActionRun deadline; SkillRun `expires_at` field |
| 15 | Cancellation | ✅ | `POST /runs/{id}/cancel` |
| 16 | Execution history | ✅ | `/runs/{id}/history` joins events + action/tool runs |

Legend: ✅ done · ⚠️ partial · ❌ not implemented

---

## Key implementations (2026-08-31)

| Area | Files |
|------|-------|
| Runtime factory + pinning | `runtime/runtime_factory.py`, `agent_service.get_publication()` |
| Optimistic locking | `skill_runs.revision`, `ConcurrentUpdateError` |
| ActionRun / ToolExecution | `domain/action_run.py`, `postgres_*_store.py`, `tables.py` |
| Multi-run routing | `runtime_service.route_all()`, `skill_routing.py` |
| Waiting resume by event type | `waiting_runs_matching_event`, worker `_matching_waiting_run` |
| Cancel / start / execute | `app/api/runtime.py` |
| List runs + summary (cockpit) | `GET /api/runtime/runs`, `/summary`, `/agents/{slug}/summary` |
| Retry / timeout / needs_human | `action_executor.py`, `tool_executor.py` |
| DLQ + correlation lock | `runtime/dlq.py`, `runtime/correlation_lock.py` |
| Scheduler | `runtime/scheduler.py`, `timer_schedules` table |
| Replay / history / metrics | `GET /runs/{id}/history`, `POST /runs/{id}/replay`, `GET /metrics` |

---

## Runtime Cockpit (UI v1)

| Route | Назначение |
|-------|------------|
| `/runtime` | Глобальный dashboard: агенты, totals, активные runs |
| `/:slug/runtime` | Per-agent cockpit: фильтры, список runs, cancel |
| `/:slug/runtime/runs/:runId` | Detail: timeline, tool logs, cancel |
| `/:slug/runtime/simulate` | Dev sandbox (publish + test events) |
| `/:slug/run` | Redirect → `/:slug/runtime/simulate` |

Backend: `GET /api/runtime/runs`, `/summary`, `/agents/{slug}/summary`, `/runs/by-conversation`.

---

## Remaining gaps

| Spec § | Topic | Status |
|--------|-------|--------|
| 18 | Correlation lock per `skill_run_id` | ⚠️ inbound/completion: `conv-skill:{conversation}:{skill}` when both known; else `run:` / entity. Not the whole conversation. Same skill on a thread is serialized (prevents forked `razgovor`). |
| 7 | `CREATED` status | ❌ |
| 24 | Parallel recipe step groups | ❌ |
| 29 | Tool `idempotent` manifest flag | ❌ |
| 43 | Production replay safeguards | ⚠️ admin/test only |
| 34 | Distributed tracing | ❌ |
| 44 | Crash recovery mid-ActionRun | ⚠️ records exist; no auto-resume |

---

## How to update this document

When implementing runtime features:

1. Change code under `E.V.A./backend/runtime/`, `workers/`, `infrastructure/stores/`.  
2. Update the relevant rows in this file (status + notes).  
3. If behavior changes the contract, update [`RUNTIME_SPEC_v0.1.md`](./RUNTIME_SPEC_v0.1.md) or mark open questions in §49.  
4. Run: `docker compose run --rm backend pytest tests/ -q`
