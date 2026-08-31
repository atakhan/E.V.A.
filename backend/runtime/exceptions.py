from __future__ import annotations


class ConcurrentUpdateError(Exception):
    """Raised when optimistic locking detects a stale SkillRun revision."""

    def __init__(self, run_id: str, expected_revision: int) -> None:
        self.run_id = run_id
        self.expected_revision = expected_revision
        super().__init__(f"Concurrent update conflict for run {run_id} (revision {expected_revision})")
