"""DTOs for review synchronization outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReviewSyncResult:
    """Result of synchronizing GitHub reviews into PostgreSQL."""

    pull_request_id: int | None
    total_processed: int
    created_count: int
    updated_count: int
    synchronized_at: datetime
