"""Tests for review synchronization service."""

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
    UnexpectedGitHubResponse,
)
from app.collector.github.models import Review as GitHubReview
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.repositories.review_repository import ReviewRepository
from app.collector.services.review_sync_service import (
    PENDING_REVIEW_SUBMITTED_AT_FALLBACK,
    ReviewSyncService,
)
from app.database.models.pull_request import PullRequest
from app.database.models.repository import Repository
from app.database.models.review import Review

SUBMITTED_AT = datetime(2024, 1, 10, tzinfo=UTC)

GITHUB_REVIEW = GitHubReview(
    github_id=5001,
    reviewer_login="alice",
    state="APPROVED",
    body="Looks good",
    submitted_at=SUBMITTED_AT,
    html_url="https://github.com/django/django/pull/42#pullrequestreview-5001",
)

UPDATED_GITHUB_REVIEW = GitHubReview(
    github_id=5001,
    reviewer_login="alice",
    state="DISMISSED",
    body="Dismissed",
    submitted_at=datetime(2024, 2, 1, tzinfo=UTC),
    html_url="https://github.com/django/django/pull/42#pullrequestreview-5001",
)

SECOND_GITHUB_REVIEW = GitHubReview(
    github_id=5002,
    reviewer_login="bob",
    state="CHANGES_REQUESTED",
    body="Please fix",
    submitted_at=datetime(2024, 1, 11, tzinfo=UTC),
    html_url="https://github.com/django/django/pull/42#pullrequestreview-5002",
)

PENDING_GITHUB_REVIEW = GitHubReview(
    github_id=5003,
    reviewer_login="carol",
    state="PENDING",
    body=None,
    submitted_at=None,
    html_url="https://github.com/django/django/pull/42#pullrequestreview-5003",
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


def _build_existing_review(
    *,
    review_id: int = 20,
    github_id: int = 5001,
    state: str = "APPROVED",
) -> Review:
    review = Review(
        github_id=github_id,
        pull_request_id=10,
        reviewer_login="alice",
        state=state,
        submitted_at=SUBMITTED_AT,
    )
    review.id = review_id
    return review


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
def sync_service(
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> ReviewSyncService:
    """Return a sync service with mocked dependencies."""
    return ReviewSyncService(
        github_client=github_client,
        repository_repository=repository_repository,
        pull_request_repository=pull_request_repository,
        review_repository=review_repository,
    )


def test_sync_pull_request_reviews_creates_new_records(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Create reviews when no local records exist."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_reviews.return_value = [GITHUB_REVIEW]
    review_repository.find_by_github_ids.return_value = {}
    review_repository.create.return_value = _build_existing_review()

    result = sync_service.sync_pull_request_reviews(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    github_client.get_reviews.assert_called_once_with("django", "django", 42)
    review_repository.find_by_github_ids.assert_called_once_with([5001])
    review_repository.create.assert_called_once_with(
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="APPROVED",
        submitted_at=SUBMITTED_AT,
    )
    review_repository.update.assert_not_called()
    assert result.pull_request_id == 10
    assert result.total_processed == 1
    assert result.created_count == 1
    assert result.updated_count == 0
    assert result.synchronized_at.tzinfo is UTC


def test_sync_pull_request_reviews_updates_existing_records(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Update reviews when they already exist locally."""
    existing = _build_existing_review()
    updated = _build_existing_review(state="DISMISSED")

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_reviews.return_value = [UPDATED_GITHUB_REVIEW]
    review_repository.find_by_github_ids.return_value = {5001: existing}
    review_repository.update.return_value = updated

    result = sync_service.sync_pull_request_reviews(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    review_repository.create.assert_not_called()
    review_repository.update.assert_called_once_with(
        existing,
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="DISMISSED",
        submitted_at=UPDATED_GITHUB_REVIEW.submitted_at,
    )
    assert result.total_processed == 1
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_pull_request_reviews_prevents_duplicates(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Use bulk lookup and update instead of creating duplicate records."""
    existing = _build_existing_review()

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_reviews.return_value = [GITHUB_REVIEW]
    review_repository.find_by_github_ids.return_value = {5001: existing}
    review_repository.update.return_value = existing

    result = sync_service.sync_pull_request_reviews(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    review_repository.create.assert_not_called()
    review_repository.update.assert_called_once()
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_pull_request_reviews_synchronizes_review_states(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Store review states exactly as received from GitHub."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_reviews.return_value = [
        GITHUB_REVIEW,
        SECOND_GITHUB_REVIEW,
        PENDING_GITHUB_REVIEW,
    ]
    review_repository.find_by_github_ids.return_value = {}
    review_repository.create.side_effect = [
        _build_existing_review(github_id=5001, state="APPROVED"),
        _build_existing_review(review_id=21, github_id=5002, state="CHANGES_REQUESTED"),
        _build_existing_review(review_id=22, github_id=5003, state="PENDING"),
    ]

    result = sync_service.sync_pull_request_reviews(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    assert review_repository.create.call_count == 3
    review_repository.create.assert_any_call(
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="APPROVED",
        submitted_at=SUBMITTED_AT,
    )
    review_repository.create.assert_any_call(
        github_id=5002,
        pull_request_id=10,
        reviewer_login="bob",
        state="CHANGES_REQUESTED",
        submitted_at=SECOND_GITHUB_REVIEW.submitted_at,
    )
    review_repository.create.assert_any_call(
        github_id=5003,
        pull_request_id=10,
        reviewer_login="carol",
        state="PENDING",
        submitted_at=PENDING_REVIEW_SUBMITTED_AT_FALLBACK,
    )
    assert result.total_processed == 3
    assert result.created_count == 3


def test_sync_repository_reviews_processes_multiple_pull_requests(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Synchronize reviews across all registered pull requests."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_id.return_value = [
        _build_local_pull_request(pull_request_id=10, number=42),
        _build_local_pull_request(pull_request_id=11, number=43),
    ]
    github_client.get_reviews.side_effect = [
        [GITHUB_REVIEW],
        [SECOND_GITHUB_REVIEW],
    ]
    review_repository.find_by_github_ids.side_effect = [{}, {}]
    review_repository.create.side_effect = [
        _build_existing_review(),
        _build_existing_review(review_id=21, github_id=5002),
    ]

    result = sync_service.sync_repository_reviews(owner="django", repository="django")

    pull_request_repository.find_by_repository_id.assert_called_once_with(1, limit=None)
    assert github_client.get_reviews.call_count == 2
    assert result.pull_request_id is None
    assert result.total_processed == 2
    assert result.created_count == 2
    assert result.updated_count == 0


def test_sync_repository_reviews_respects_limit(
    sync_service: ReviewSyncService,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    github_client: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Pass the processing limit to the pull request lookup."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_id.return_value = [
        _build_local_pull_request(),
    ]
    github_client.get_reviews.return_value = []
    review_repository.find_by_github_ids.return_value = {}

    sync_service.sync_repository_reviews(
        owner="django",
        repository="django",
        limit=5,
    )

    pull_request_repository.find_by_repository_id.assert_called_once_with(1, limit=5)


def test_sync_pull_request_reviews_raises_when_repository_not_registered(
    sync_service: ReviewSyncService,
    repository_repository: MagicMock,
    github_client: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Raise RepositoryNotFound when the repository is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = None

    with pytest.raises(RepositoryNotFound):
        sync_service.sync_pull_request_reviews(
            owner="django",
            repository="missing",
            pull_request_number=42,
        )

    github_client.get_reviews.assert_not_called()
    review_repository.create.assert_not_called()
    review_repository.update.assert_not_called()


def test_sync_pull_request_reviews_raises_when_pull_request_not_registered(
    sync_service: ReviewSyncService,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    github_client: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Raise PullRequestNotFound when the pull request is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = None

    with pytest.raises(PullRequestNotFound):
        sync_service.sync_pull_request_reviews(
            owner="django",
            repository="django",
            pull_request_number=999,
        )

    github_client.get_reviews.assert_not_called()
    review_repository.create.assert_not_called()
    review_repository.update.assert_not_called()


def test_sync_pull_request_reviews_raises_pull_request_not_found_from_github(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Propagate PullRequestNotFound from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_reviews.side_effect = PullRequestNotFound(
        "Pull request not found",
    )

    with pytest.raises(PullRequestNotFound):
        sync_service.sync_pull_request_reviews(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_repository.create.assert_not_called()
    review_repository.update.assert_not_called()


def test_sync_pull_request_reviews_raises_authentication_error(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Propagate AuthenticationError from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_reviews.side_effect = AuthenticationError(
        "GitHub authentication failed.",
    )

    with pytest.raises(AuthenticationError):
        sync_service.sync_pull_request_reviews(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_repository.create.assert_not_called()
    review_repository.update.assert_not_called()


def test_sync_pull_request_reviews_raises_rate_limit_exceeded(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
) -> None:
    """Propagate RateLimitExceeded from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_reviews.side_effect = RateLimitExceeded(
        "GitHub rate limit exceeded.",
        remaining=0,
        reset_at=1_700_000_000,
    )

    with pytest.raises(RateLimitExceeded):
        sync_service.sync_pull_request_reviews(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    review_repository.create.assert_not_called()
    review_repository.update.assert_not_called()


def test_sync_pull_request_reviews_raises_unexpected_github_response(
    sync_service: ReviewSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    review_repository: MagicMock,
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
        url="https://api.github.com/repos/django/django/pulls/42/reviews",
        body="Internal Server Error",
        headers={},
    )
    github_client.get_reviews.side_effect = UnexpectedGitHubResponse(
        "Unexpected GitHub response.",
        response=response,
    )

    with pytest.raises(UnexpectedGitHubResponse) as exc_info:
        sync_service.sync_pull_request_reviews(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    assert exc_info.value.status_code == 500
    review_repository.create.assert_not_called()
    review_repository.update.assert_not_called()
