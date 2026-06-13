"""CLI dependency wiring for configuration and service creation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collector.config import GitHubSettings
from app.collector.github.client import GitHubClient
from app.collector.repositories.file_change_repository import FileChangeRepository
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.repositories.review_comment_repository import ReviewCommentRepository
from app.collector.repositories.review_repository import ReviewRepository
from app.collector.services.file_change_sync_service import FileChangeSyncService
from app.collector.services.pull_request_sync_service import PullRequestSyncService
from app.collector.services.repository_sync_service import RepositorySyncService
from app.collector.services.review_comment_sync_service import ReviewCommentSyncService
from app.collector.services.review_sync_service import ReviewSyncService
from app.database.config import DatabaseSettings
from app.database.models.file_change import FileChange
from app.database.models.pull_request import PullRequest
from app.database.models.repository import Repository
from app.database.models.review import Review
from app.database.models.review_comment import ReviewComment
from app.database.session import session_scope


@dataclass(frozen=True, slots=True)
class CliSettings:
    """Centralized CLI configuration loaded from environment variables."""

    github: GitHubSettings
    database: DatabaseSettings


@dataclass(frozen=True, slots=True)
class CollectionStats:
    """Read-only counts of persisted collection entities."""

    repositories: int
    pull_requests: int
    reviews: int
    review_comments: int
    file_changes: int


def load_cli_settings() -> CliSettings:
    """Load GitHub and database settings from environment variables."""
    return CliSettings(
        github=GitHubSettings.from_env(),
        database=DatabaseSettings.from_env(),
    )


def create_github_client(settings: CliSettings) -> GitHubClient:
    """Create a GitHub API client from CLI settings."""
    return GitHubClient(settings.github)


def _query_collection_stats(session: Session) -> CollectionStats:
    """Return entity counts from the database."""
    repositories = session.scalar(select(func.count()).select_from(Repository)) or 0
    pull_requests = session.scalar(select(func.count()).select_from(PullRequest)) or 0
    reviews = session.scalar(select(func.count()).select_from(Review)) or 0
    review_comments = (
        session.scalar(select(func.count()).select_from(ReviewComment)) or 0
    )
    file_changes = session.scalar(select(func.count()).select_from(FileChange)) or 0
    return CollectionStats(
        repositories=repositories,
        pull_requests=pull_requests,
        reviews=reviews,
        review_comments=review_comments,
        file_changes=file_changes,
    )


def fetch_collection_stats(
    cli_settings: CliSettings | None = None,
) -> CollectionStats:
    """Fetch read-only collection statistics from the database."""
    settings = cli_settings or load_cli_settings()
    with session_scope(settings.database) as session:
        return _query_collection_stats(session)


@contextmanager
def repository_sync_service(
    cli_settings: CliSettings | None = None,
) -> Iterator[RepositorySyncService]:
    """Provide a repository synchronization service within a database session."""
    settings = cli_settings or load_cli_settings()
    with session_scope(settings.database) as session:
        yield RepositorySyncService(
            create_github_client(settings),
            RepositoryRepository(session),
        )


@contextmanager
def pull_request_sync_service(
    cli_settings: CliSettings | None = None,
) -> Iterator[PullRequestSyncService]:
    """Provide a pull request synchronization service within a database session."""
    settings = cli_settings or load_cli_settings()
    with session_scope(settings.database) as session:
        yield PullRequestSyncService(
            create_github_client(settings),
            RepositoryRepository(session),
            PullRequestRepository(session),
        )


@contextmanager
def review_sync_service(
    cli_settings: CliSettings | None = None,
) -> Iterator[ReviewSyncService]:
    """Provide a review synchronization service within a database session."""
    settings = cli_settings or load_cli_settings()
    with session_scope(settings.database) as session:
        yield ReviewSyncService(
            create_github_client(settings),
            RepositoryRepository(session),
            PullRequestRepository(session),
            ReviewRepository(session),
        )


@contextmanager
def review_comment_sync_service(
    cli_settings: CliSettings | None = None,
) -> Iterator[ReviewCommentSyncService]:
    """Provide a review comment synchronization service within a database session."""
    settings = cli_settings or load_cli_settings()
    with session_scope(settings.database) as session:
        yield ReviewCommentSyncService(
            create_github_client(settings),
            RepositoryRepository(session),
            PullRequestRepository(session),
            ReviewRepository(session),
            ReviewCommentRepository(session),
        )


@contextmanager
def file_change_sync_service(
    cli_settings: CliSettings | None = None,
) -> Iterator[FileChangeSyncService]:
    """Provide a file change synchronization service within a database session."""
    settings = cli_settings or load_cli_settings()
    with session_scope(settings.database) as session:
        yield FileChangeSyncService(
            create_github_client(settings),
            RepositoryRepository(session),
            PullRequestRepository(session),
            FileChangeRepository(session),
        )
