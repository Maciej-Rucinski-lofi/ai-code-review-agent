"""DTOs for review comment synchronization outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReviewCommentSyncResult:
    """Result of synchronizing GitHub review comments into PostgreSQL."""

    pull_request_id: int | None
    total_processed: int
    created_count: int
    updated_count: int
    synchronized_at: datetime
