"""DTOs for repository synchronization outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RepositorySyncAction(StrEnum):
    """Outcome of a repository synchronization operation."""

    CREATED = "created"
    UPDATED = "updated"


@dataclass(frozen=True, slots=True)
class RepositorySyncResult:
    """Result of synchronizing a GitHub repository into PostgreSQL."""

    repository_id: int
    github_id: int
    action: RepositorySyncAction
    synchronized_at: datetime
