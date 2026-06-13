"""Tests for CLI command registration, execution, and error handling."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError
from typer.testing import CliRunner

from app.cli.dependencies import CollectionStats
from app.cli.main import app
from app.collector.github.exceptions import (
    AuthenticationError,
    RateLimitExceeded,
    RepositoryNotFound,
)
from app.collector.schemas.pull_request_sync_result import PullRequestSyncResult
from app.collector.schemas.repository_sync_result import (
    RepositorySyncAction,
    RepositorySyncResult,
)
from app.collector.schemas.review_comment_sync_result import ReviewCommentSyncResult
from app.collector.schemas.review_sync_result import ReviewSyncResult
from app.collector.schemas.file_change_sync_result import FileChangeSyncResult

if TYPE_CHECKING:
    from collections.abc import Iterator

runner = CliRunner()

SYNC_TIMESTAMP = datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "command_name",
    [
        "sync-repository",
        "sync-prs",
        "sync-reviews",
        "sync-comments",
        "sync-files",
        "stats",
    ],
)
def test_commands_are_registered(command_name: str) -> None:
    """Each CLI command should appear in the application help output."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert command_name in result.stdout


def test_sync_repository_invokes_service() -> None:
    """sync-repository should call the repository sync service and display results."""
    service = MagicMock()
    service.sync_repository.return_value = RepositorySyncResult(
        repository_id=1,
        github_id=123,
        action=RepositorySyncAction.CREATED,
        synchronized_at=SYNC_TIMESTAMP,
    )

    with patch(
        "app.cli.commands.repository.repository_sync_service",
        return_value=_context_manager(service),
    ):
        result = runner.invoke(app, ["sync-repository", "django", "django"])

    assert result.exit_code == 0
    service.sync_repository.assert_called_once_with("django", "django")
    assert "Repository: django/django" in result.stdout
    assert "Action: created" in result.stdout
    assert "Execution time:" in result.stdout


def test_sync_prs_invokes_service_with_max_pages() -> None:
    """sync-prs should forward max-pages to the pull request sync service."""
    service = MagicMock()
    service.sync_repository_pull_requests.return_value = PullRequestSyncResult(
        repository_id=1,
        total_processed=10,
        created_count=7,
        updated_count=3,
        synchronized_at=SYNC_TIMESTAMP,
    )

    with patch(
        "app.cli.commands.pull_request.pull_request_sync_service",
        return_value=_context_manager(service),
    ):
        result = runner.invoke(
            app,
            ["sync-prs", "django", "django", "--max-pages", "10"],
        )

    assert result.exit_code == 0
    service.sync_repository_pull_requests.assert_called_once_with(
        "django",
        "django",
        max_pages=10,
    )
    assert "Total processed: 10" in result.stdout
    assert "Created: 7" in result.stdout
    assert "Updated: 3" in result.stdout


def test_sync_prs_rejects_invalid_max_pages() -> None:
    """sync-prs should reject non-positive max-pages values."""
    result = runner.invoke(
        app,
        ["sync-prs", "django", "django", "--max-pages", "0"],
    )

    assert result.exit_code != 0


def test_sync_reviews_invokes_service() -> None:
    """sync-reviews should call the review sync service."""
    service = MagicMock()
    service.sync_repository_reviews.return_value = ReviewSyncResult(
        pull_request_id=None,
        total_processed=4,
        created_count=2,
        updated_count=2,
        synchronized_at=SYNC_TIMESTAMP,
    )

    with patch(
        "app.cli.commands.review.review_sync_service",
        return_value=_context_manager(service),
    ):
        result = runner.invoke(app, ["sync-reviews", "django", "django"])

    assert result.exit_code == 0
    service.sync_repository_reviews.assert_called_once_with("django", "django")
    assert "Total processed: 4" in result.stdout


def test_sync_comments_invokes_service() -> None:
    """sync-comments should call the review comment sync service."""
    service = MagicMock()
    service.sync_repository_comments.return_value = ReviewCommentSyncResult(
        pull_request_id=None,
        total_processed=6,
        created_count=5,
        updated_count=1,
        synchronized_at=SYNC_TIMESTAMP,
    )

    with patch(
        "app.cli.commands.review_comment.review_comment_sync_service",
        return_value=_context_manager(service),
    ):
        result = runner.invoke(app, ["sync-comments", "django", "django"])

    assert result.exit_code == 0
    service.sync_repository_comments.assert_called_once_with("django", "django")
    assert "Total processed: 6" in result.stdout


def test_sync_files_invokes_service() -> None:
    """sync-files should call the file change sync service."""
    service = MagicMock()
    service.sync_repository_files.return_value = FileChangeSyncResult(
        pull_request_id=None,
        total_processed=8,
        created_count=6,
        updated_count=2,
        synchronized_at=SYNC_TIMESTAMP,
    )

    with patch(
        "app.cli.commands.file_change.file_change_sync_service",
        return_value=_context_manager(service),
    ):
        result = runner.invoke(app, ["sync-files", "django", "django"])

    assert result.exit_code == 0
    service.sync_repository_files.assert_called_once_with("django", "django")
    assert "Total processed: 8" in result.stdout


def test_stats_displays_collection_counts() -> None:
    """stats should display read-only counts from the database layer."""
    with patch(
        "app.cli.commands.stats.fetch_collection_stats",
        return_value=CollectionStats(
            repositories=1,
            pull_requests=20,
            reviews=15,
            review_comments=40,
            file_changes=100,
        ),
    ):
        result = runner.invoke(app, ["stats"])

    assert result.exit_code == 0
    assert "Repositories: 1" in result.stdout
    assert "Pull Requests: 20" in result.stdout
    assert "Reviews: 15" in result.stdout
    assert "Review Comments: 40" in result.stdout
    assert "File Changes: 100" in result.stdout


@pytest.mark.parametrize(
    ("command", "args", "patch_target", "side_effect", "expected_message"),
    [
        (
            "sync-repository",
            ["django", "django"],
            "app.cli.commands.repository.repository_sync_service",
            RepositoryNotFound("Repository django/missing was not found."),
            "Repository not found",
        ),
        (
            "sync-repository",
            ["django", "django"],
            "app.cli.commands.repository.repository_sync_service",
            AuthenticationError("Bad credentials"),
            "GitHub authentication failed",
        ),
        (
            "sync-prs",
            ["django", "django"],
            "app.cli.commands.pull_request.pull_request_sync_service",
            RateLimitExceeded("Rate limit exceeded"),
            "GitHub rate limit exceeded",
        ),
        (
            "stats",
            [],
            "app.cli.commands.stats.fetch_collection_stats",
            OperationalError("connection refused", None, None),
            "Database connection failed",
        ),
    ],
)
def test_error_handling_returns_non_zero_exit_code(
    command: str,
    args: list[str],
    patch_target: str,
    side_effect: Exception,
    expected_message: str,
) -> None:
    """CLI failures should produce user-friendly messages and non-zero exit codes."""
    if command == "stats":
        with patch(patch_target, side_effect=side_effect):
            result = runner.invoke(app, [command, *args])
    else:
        service = MagicMock()
        if command == "sync-repository":
            service.sync_repository.side_effect = side_effect
        elif command == "sync-prs":
            service.sync_repository_pull_requests.side_effect = side_effect

        with patch(patch_target, return_value=_context_manager(service)):
            result = runner.invoke(app, [command, *args])

    assert result.exit_code != 0
    assert expected_message in result.output
    assert "Traceback" not in result.output


@contextmanager
def _context_manager(service: MagicMock) -> Iterator[MagicMock]:
    """Provide a mock service through a context manager interface."""
    yield service
