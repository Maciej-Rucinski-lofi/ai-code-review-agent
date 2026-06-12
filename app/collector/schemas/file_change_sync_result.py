"""DTOs for file change synchronization outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FileChangeSyncResult:
    """Result of synchronizing GitHub pull request file changes into PostgreSQL."""

    pull_request_id: int | None
    total_processed: int
    created_count: int
    updated_count: int
    synchronized_at: datetime
