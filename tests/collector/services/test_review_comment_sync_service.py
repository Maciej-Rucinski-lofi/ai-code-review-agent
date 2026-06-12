"""Tests for review comment synchronization service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from app.collector.github.client import GitHubClient
from app.collector.github.exceptions import (
    AuthenticationError,
    GitHubResponseInfo,
    PullRequestNotFound,
    RateLimitExceeded,
    RepositoryNotFound,
    ReviewNotFound,
    UnexpectedGitHubResponse,
)
from app.collector.github.models import ReviewComment as GitHubReviewComment
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.repositories.review_comment_repository import ReviewCommentRepository
from app.collector.repositories.review_repository import ReviewRepository
from app.collector.services.review_comment_sync_service import ReviewCommentSyncService
from app.database.models.pull_request import PullRequest
from app.database.models.repository import Repository
from app.database.models.review import Review
from app.database.models.review_comment import ReviewComment

CREATED_AT = datetime(2024, 1, 2, 7, 30, tzinfo=UTC)
UPDATED_CREATED_AT = datetime(2024, 2, 1, tzinfo=UTC)

GITHUB_COMMENT = GitHubReviewComment(
    github_id=1011,
    author_login="bob",
    body="Consider renaming this variable.",
    file_path="django/db/models/query.py",
    line_number=12,
    original_line_number=10,
    diff_hunk="@@ -10,3 +10,4 @@",
    created_at=CREATED_AT,
    pull_request_review_id=789,
    html_url="https://github.com/django/django/pull/42#discussion_r1011",
)

UPDATED_GITHUB_COMMENT = GitHubReviewComment(
    github_id=1011,
    author_login="bob",
    body="Please rename this variable for clarity.",
    file_path="django/db/models/query.py",
    line_number=14,
    original_line_number=10,
    diff_hunk="@@ -10,3 +10,4 @@",
    created_at=UPDATED_CREATED_AT,
    pull_request_review_id=789,
    html_url="https://github.com/django/django/pull/42#discussion_r1011",
)

SECOND_GITHUB_COMMENT = GitHubReviewComment(
    github_id=1012,
    author_login="alice",
    body="Missing type hint.",
    file_path="django/db/models/base.py",
    line_number=5,
    original_line_number=5,
    diff_hunk="@@ -5,1 +5,1 @@",
    created_at=datetime(2024, 1, 3, tzinfo=UTC),
    pull_request_review_id=790,
    html_url="https://github.com/django/django/pull/42#discussion_r1012",
)

COMMENT_WITHOUT_REVIEW = GitHubReviewComment(
    github_id=1013,
    author_login="carol",
    body="Standalone comment",
    file_path="django/db/models/base.py",
    line_number=8,
    original_line_number=8,
    diff_hunk=None,
    created_at=datetime(2024, 1, 4, tzinfo=UTC),
    pull_request_review_id=None,
    html_url="https://github.com/django/django/pull/42#discussion_r1013",
)


def _build_local_repository(*, repository_id: int = 1) -> Repository:
    repository = Repository(
        github_id=123,
        owner="django",
        name="django",
        description=None,
        default_branch="main",
    )
    repository.id = repository_id
    return repository


def _build_local_pull_request(
    *,
    pull_request_id: int = 10,
    number: int = 42,
) -> PullRequest:
    pull_request = PullRequest(
        github_id=1001,
        repository_id=1,
        number=number,
        title="Fix bug",
        body="Description",
        state="closed",
        author_login="alice",
        merged_at=datetime(2024, 1, 3, tzinfo=UTC),
    )
    pull_request.id = pull_request_id
    return pull_request


def _build_local_review(
    *,
    review_id: int = 20,
    github_id: int = 789,
) -> Review:
    review = Review(
        github_id=github_id,
        pull_request_id=10,
        reviewer_login="bob",
        state="COMMENTED",
        submitted_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
    review.id = review_id
    return review


def _build_existing_comment(
    *,
    comment_id: int = 30,
    github_id: int = 1011,
    review_id: int = 20,
) -> ReviewComment:
    comment = ReviewComment(
        github_id=github_id,
        review_id=review_id,
        pull_request_id=10,
        body="Consider renaming this variable.",
        file_path="django/db/models/query.py",
        line_number=12,
        created_at=CREATED_AT,
    )
    comment.id = comment_id
    return comment


@pytest.fixture
def github_client() -> MagicMock:
    """Return a mocked GitHub client."""
    return create_autospec(GitHubClient, instance=True)


@pytest.fixture
def repository_repository() -> MagicMock:
    """Return a mocked repository persistence layer."""
    return create_autospec(RepositoryRepository, instance=True)


@pytest.fixture
def pull_request_repository() -> MagicMock:
    """Return a mocked pull request persistence layer."""
    return create_autospec(PullRequestRepository, instance=True)


@pytest.fixture
def review_repository() -> MagicMock:
    """Return a mocked review persistence layer."""
    return create_autospec(ReviewRepository, instance=True)


@pytest.fixture
def review_comment_repository() -> MagicMock:
    """Return a mocked review comment persistence layer."""
    return create_autospec(ReviewCommentRepository, instance=True)


@pytest.fixture
def sync_service(
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> ReviewCommentSyncService:
    """Return a sync service with mocked dependencies."""
    return ReviewCommentSyncService(
        github_client=github_client,
        repository_repository=repository_repository,
        pull_request_repository=pull_request_repository,
        review_repository=review_repository,
        review_comment_repository=review_comment_repository,
    )


def test_sync_pull_request_comments_creates_new_records(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Create review comments when no local records exist."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.return_value = [GITHUB_COMMENT]
    review_repository.find_by_github_ids.return_value = {789: _build_local_review()}
    review_comment_repository.find_by_github_ids.return_value = {}
    review_comment_repository.create.return_value = _build_existing_comment()

    result = sync_service.sync_pull_request_comments(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    github_client.get_review_comments.assert_called_once_with("django", "django", 42)
    review_repository.find_by_github_ids.assert_called_once_with([789])
    review_comment_repository.find_by_github_ids.assert_called_once_with([1011])
    review_comment_repository.create.assert_called_once_with(
        github_id=1011,
        review_id=20,
        pull_request_id=10,
        body="Consider renaming this variable.",
        file_path="django/db/models/query.py",
        line_number=12,
        created_at=CREATED_AT,
    )
    review_comment_repository.update.assert_not_called()
    assert result.pull_request_id == 10
    assert result.total_processed == 1
    assert result.created_count == 1
    assert result.updated_count == 0
    assert result.synchronized_at.tzinfo is UTC


def test_sync_pull_request_comments_updates_existing_records(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Update review comments when they already exist locally."""
    existing = _build_existing_comment()
    updated = _build_existing_comment()

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.return_value = [UPDATED_GITHUB_COMMENT]
    review_repository.find_by_github_ids.return_value = {789: _build_local_review()}
    review_comment_repository.find_by_github_ids.return_value = {1011: existing}
    review_comment_repository.update.return_value = updated

    result = sync_service.sync_pull_request_comments(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_called_once_with(
        existing,
        github_id=1011,
        review_id=20,
        pull_request_id=10,
        body="Please rename this variable for clarity.",
        file_path="django/db/models/query.py",
        line_number=14,
        created_at=UPDATED_CREATED_AT,
    )
    assert result.total_processed == 1
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_pull_request_comments_prevents_duplicates(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Use bulk lookup and update instead of creating duplicate records."""
    existing = _build_existing_comment()

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.return_value = [GITHUB_COMMENT]
    review_repository.find_by_github_ids.return_value = {789: _build_local_review()}
    review_comment_repository.find_by_github_ids.return_value = {1011: existing}
    review_comment_repository.update.return_value = existing

    result = sync_service.sync_pull_request_comments(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_called_once()
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_pull_request_comments_maps_review_relationships(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Map comments to locally synchronized reviews by GitHub review identifier."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.return_value = [
        GITHUB_COMMENT,
        SECOND_GITHUB_COMMENT,
    ]
    review_repository.find_by_github_ids.return_value = {
        789: _build_local_review(review_id=20, github_id=789),
        790: _build_local_review(review_id=21, github_id=790),
    }
    review_comment_repository.find_by_github_ids.return_value = {}
    review_comment_repository.create.side_effect = [
        _build_existing_comment(comment_id=30, github_id=1011, review_id=20),
        _build_existing_comment(comment_id=31, github_id=1012, review_id=21),
    ]

    result = sync_service.sync_pull_request_comments(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    review_repository.find_by_github_ids.assert_called_once_with([789, 790])
    assert review_comment_repository.create.call_count == 2
    review_comment_repository.create.assert_any_call(
        github_id=1011,
        review_id=20,
        pull_request_id=10,
        body=GITHUB_COMMENT.body,
        file_path=GITHUB_COMMENT.file_path,
        line_number=GITHUB_COMMENT.line_number,
        created_at=GITHUB_COMMENT.created_at,
    )
    review_comment_repository.create.assert_any_call(
        github_id=1012,
        review_id=21,
        pull_request_id=10,
        body=SECOND_GITHUB_COMMENT.body,
        file_path=SECOND_GITHUB_COMMENT.file_path,
        line_number=SECOND_GITHUB_COMMENT.line_number,
        created_at=SECOND_GITHUB_COMMENT.created_at,
    )
    assert result.total_processed == 2
    assert result.created_count == 2


def test_sync_repository_comments_processes_multiple_pull_requests(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Synchronize review comments across all registered pull requests."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_id.return_value = [
        _build_local_pull_request(pull_request_id=10, number=42),
        _build_local_pull_request(pull_request_id=11, number=43),
    ]
    github_client.get_review_comments.side_effect = [
        [GITHUB_COMMENT],
        [SECOND_GITHUB_COMMENT],
    ]
    review_repository.find_by_github_ids.side_effect = [
        {789: _build_local_review()},
        {790: _build_local_review(review_id=21, github_id=790)},
    ]
    review_comment_repository.find_by_github_ids.side_effect = [{}, {}]
    review_comment_repository.create.side_effect = [
        _build_existing_comment(),
        _build_existing_comment(comment_id=31, github_id=1012, review_id=21),
    ]

    result = sync_service.sync_repository_comments(owner="django", repository="django")

    pull_request_repository.find_by_repository_id.assert_called_once_with(1, limit=None)
    assert github_client.get_review_comments.call_count == 2
    assert result.pull_request_id is None
    assert result.total_processed == 2
    assert result.created_count == 2
    assert result.updated_count == 0


def test_sync_repository_comments_respects_limit(
    sync_service: ReviewCommentSyncService,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    github_client: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Pass the processing limit to the pull request lookup."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_id.return_value = [
        _build_local_pull_request(),
    ]
    github_client.get_review_comments.return_value = []
    review_repository.find_by_github_ids.return_value = {}
    review_comment_repository.find_by_github_ids.return_value = {}

    sync_service.sync_repository_comments(
        owner="django",
        repository="django",
        limit=5,
    )

    pull_request_repository.find_by_repository_id.assert_called_once_with(1, limit=5)


def test_sync_pull_request_comments_raises_when_repository_not_registered(
    sync_service: ReviewCommentSyncService,
    repository_repository: MagicMock,
    github_client: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Raise RepositoryNotFound when the repository is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = None

    with pytest.raises(RepositoryNotFound):
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="missing",
            pull_request_number=42,
        )

    github_client.get_review_comments.assert_not_called()
    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()


def test_sync_pull_request_comments_raises_when_pull_request_not_registered(
    sync_service: ReviewCommentSyncService,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    github_client: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Raise PullRequestNotFound when the pull request is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = None

    with pytest.raises(PullRequestNotFound):
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="django",
            pull_request_number=999,
        )

    github_client.get_review_comments.assert_not_called()
    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()


def test_sync_pull_request_comments_raises_when_review_not_registered(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Raise ReviewNotFound when the parent review is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.return_value = [GITHUB_COMMENT]
    review_repository.find_by_github_ids.return_value = {}
    review_comment_repository.find_by_github_ids.return_value = {}

    with pytest.raises(ReviewNotFound):
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()


def test_sync_pull_request_comments_raises_when_comment_has_no_review(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Raise ReviewNotFound when GitHub comment is not linked to a review."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.return_value = [COMMENT_WITHOUT_REVIEW]
    review_repository.find_by_github_ids.return_value = {}
    review_comment_repository.find_by_github_ids.return_value = {}

    with pytest.raises(ReviewNotFound):
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()


def test_sync_pull_request_comments_raises_pull_request_not_found_from_github(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Propagate PullRequestNotFound from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.side_effect = PullRequestNotFound(
        "Pull request not found",
    )

    with pytest.raises(PullRequestNotFound):
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()


def test_sync_pull_request_comments_raises_authentication_error(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Propagate AuthenticationError from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.side_effect = AuthenticationError(
        "GitHub authentication failed.",
    )

    with pytest.raises(AuthenticationError):
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()


def test_sync_pull_request_comments_raises_rate_limit_exceeded(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Propagate RateLimitExceeded from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_review_comments.side_effect = RateLimitExceeded(
        "GitHub rate limit exceeded.",
        remaining=0,
        reset_at=1_700_000_000,
    )

    with pytest.raises(RateLimitExceeded):
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()


def test_sync_pull_request_comments_raises_unexpected_github_response(
    sync_service: ReviewCommentSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_comment_repository: MagicMock,
) -> None:
    """Propagate UnexpectedGitHubResponse from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    response = GitHubResponseInfo(
        status_code=500,
        url="https://api.github.com/repos/django/django/pulls/42/comments",
        body="Internal Server Error",
        headers={},
    )
    github_client.get_review_comments.side_effect = UnexpectedGitHubResponse(
        "Unexpected GitHub response.",
        response=response,
    )

    with pytest.raises(UnexpectedGitHubResponse) as exc_info:
        sync_service.sync_pull_request_comments(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    assert exc_info.value.status_code == 500
    review_comment_repository.create.assert_not_called()
    review_comment_repository.update.assert_not_called()
