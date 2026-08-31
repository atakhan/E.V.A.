from __future__ import annotations

_events_processed = 0
_runs_active = 0
_action_failures = 0


def inc_events_processed(count: int = 1) -> None:
    global _events_processed
    _events_processed += count


def inc_action_failures(count: int = 1) -> None:
    global _action_failures
    _action_failures += count


def set_runs_active(count: int) -> None:
    global _runs_active
    _runs_active = count


def snapshot() -> dict[str, int]:
    return {
        "events_processed": _events_processed,
        "runs_active": _runs_active,
        "action_failures": _action_failures,
    }
