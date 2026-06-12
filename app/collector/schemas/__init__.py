"""Collector data transfer objects."""

from app.collector.schemas.pull_request_sync_result import PullRequestSyncResult
from app.collector.schemas.repository_sync_result import (
    RepositorySyncAction,
    RepositorySyncResult,
)

__all__ = [
    "PullRequestSyncResult",
    "RepositorySyncAction",
    "RepositorySyncResult",
]
