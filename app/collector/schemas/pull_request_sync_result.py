"""DTOs for pull request synchronization outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PullRequestSyncResult:
    """Result of synchronizing GitHub pull requests into PostgreSQL."""

    repository_id: int
    total_processed: int
    created_count: int
    updated_count: int
    synchronized_at: datetime
