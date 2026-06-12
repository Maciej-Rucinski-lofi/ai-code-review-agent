"""Tests for pull request synchronization service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from app.collector.github.client import GitHubClient
from app.collector.github.exceptions import (
    AuthenticationError,
    GitHubResponseInfo,
    RateLimitExceeded,
    RepositoryNotFound,
    UnexpectedGitHubResponse,
)
from app.collector.github.models import PaginatedResponse, PaginationInfo
from app.collector.github.models import PullRequest as GitHubPullRequest
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.services.pull_request_sync_service import PullRequestSyncService
from app.database.models.pull_request import PullRequest
from app.database.models.repository import Repository

CREATED_AT = datetime(2024, 1, 1, tzinfo=UTC)
UPDATED_AT = datetime(2024, 1, 2, tzinfo=UTC)
MERGED_AT = datetime(2024, 1, 3, tzinfo=UTC)

GITHUB_PULL_REQUEST = GitHubPullRequest(
    github_id=1001,
    number=42,
    title="Fix bug",
    body="Description",
    state="closed",
    author_login="alice",
    merged_at=MERGED_AT,
    created_at=CREATED_AT,
    updated_at=UPDATED_AT,
    html_url="https://github.com/django/django/pull/42",
)

UPDATED_GITHUB_PULL_REQUEST = GitHubPullRequest(
    github_id=1001,
    number=42,
    title="Fix bug updated",
    body="Updated description",
    state="closed",
    author_login="alice",
    merged_at=MERGED_AT,
    created_at=CREATED_AT,
    updated_at=datetime(2024, 2, 1, tzinfo=UTC),
    html_url="https://github.com/django/django/pull/42",
)

SECOND_GITHUB_PULL_REQUEST = GitHubPullRequest(
    github_id=1002,
    number=43,
    title="Add feature",
    body=None,
    state="open",
    author_login="bob",
    merged_at=None,
    created_at=datetime(2024, 1, 4, tzinfo=UTC),
    updated_at=datetime(2024, 1, 5, tzinfo=UTC),
    html_url="https://github.com/django/django/pull/43",
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


def _build_existing_pull_request(
    *,
    pull_request_id: int = 10,
    github_id: int = 1001,
    number: int = 42,
    title: str = "Fix bug",
) -> PullRequest:
    pull_request = PullRequest(
        github_id=github_id,
        repository_id=1,
        number=number,
        title=title,
        body="Description",
        state="closed",
        author_login="alice",
        merged_at=MERGED_AT,
    )
    pull_request.id = pull_request_id
    return pull_request


def _build_paginated_response(
    items: list[GitHubPullRequest],
    *,
    current_page: int,
    has_next: bool,
) -> PaginatedResponse[GitHubPullRequest]:
    next_page = current_page + 1 if has_next else None
    return PaginatedResponse(
        items=items,
        pagination=PaginationInfo(
            current_page=current_page,
            next_page=next_page,
            previous_page=current_page - 1 if current_page > 1 else None,
            last_page=next_page,
            first_page=1,
            next_url=f"https://api.github.com?page={next_page}" if has_next else None,
            previous_url=None,
            last_url=None,
            first_url=None,
        ),
    )


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
def sync_service(
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> PullRequestSyncService:
    """Return a sync service with mocked dependencies."""
    return PullRequestSyncService(
        github_client=github_client,
        repository_repository=repository_repository,
        pull_request_repository=pull_request_repository,
    )


def test_sync_recent_pull_requests_creates_new_records(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Create pull requests when no local records exist."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.return_value = _build_paginated_response(
        [GITHUB_PULL_REQUEST],
        current_page=1,
        has_next=False,
    )
    pull_request_repository.find_by_github_ids.return_value = {}
    pull_request_repository.create.return_value = _build_existing_pull_request()

    result = sync_service.sync_recent_pull_requests(owner="django", repository="django")

    github_client.get_pull_requests.assert_called_once_with(
        "django",
        "django",
        "all",
        page=1,
        per_page=100,
    )
    pull_request_repository.find_by_github_ids.assert_called_once_with([1001])
    pull_request_repository.create.assert_called_once_with(
        github_id=1001,
        repository_id=1,
        number=42,
        title="Fix bug",
        body="Description",
        state="closed",
        author_login="alice",
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        merged_at=MERGED_AT,
    )
    pull_request_repository.update.assert_not_called()
    assert result.repository_id == 1
    assert result.total_processed == 1
    assert result.created_count == 1
    assert result.updated_count == 0
    assert result.synchronized_at.tzinfo is UTC


def test_sync_recent_pull_requests_updates_existing_records(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Update pull requests when they already exist locally."""
    existing = _build_existing_pull_request()
    updated = _build_existing_pull_request(title="Fix bug updated")

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.return_value = _build_paginated_response(
        [UPDATED_GITHUB_PULL_REQUEST],
        current_page=1,
        has_next=False,
    )
    pull_request_repository.find_by_github_ids.return_value = {1001: existing}
    pull_request_repository.update.return_value = updated

    result = sync_service.sync_recent_pull_requests(owner="django", repository="django")

    pull_request_repository.create.assert_not_called()
    pull_request_repository.update.assert_called_once_with(
        existing,
        github_id=1001,
        repository_id=1,
        number=42,
        title="Fix bug updated",
        body="Updated description",
        state="closed",
        author_login="alice",
        created_at=CREATED_AT,
        updated_at=UPDATED_GITHUB_PULL_REQUEST.updated_at,
        merged_at=MERGED_AT,
    )
    assert result.total_processed == 1
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_repository_pull_requests_handles_pagination(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Fetch and synchronize multiple pages until pagination ends."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.side_effect = [
        _build_paginated_response(
            [GITHUB_PULL_REQUEST],
            current_page=1,
            has_next=True,
        ),
        _build_paginated_response(
            [SECOND_GITHUB_PULL_REQUEST],
            current_page=2,
            has_next=False,
        ),
    ]
    pull_request_repository.find_by_github_ids.side_effect = [{}, {}]
    pull_request_repository.create.side_effect = [
        _build_existing_pull_request(),
        _build_existing_pull_request(github_id=1002, number=43),
    ]

    result = sync_service.sync_repository_pull_requests(
        owner="django",
        repository="django",
    )

    assert github_client.get_pull_requests.call_count == 2
    github_client.get_pull_requests.assert_any_call(
        "django",
        "django",
        "all",
        page=1,
        per_page=100,
    )
    github_client.get_pull_requests.assert_any_call(
        "django",
        "django",
        "all",
        page=2,
        per_page=100,
    )
    assert pull_request_repository.find_by_github_ids.call_count == 2
    assert pull_request_repository.create.call_count == 2
    assert result.total_processed == 2
    assert result.created_count == 2
    assert result.updated_count == 0


def test_sync_repository_pull_requests_respects_max_pages(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Stop pagination after the configured maximum page count."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.return_value = _build_paginated_response(
        [GITHUB_PULL_REQUEST],
        current_page=1,
        has_next=True,
    )
    pull_request_repository.find_by_github_ids.return_value = {}
    pull_request_repository.create.return_value = _build_existing_pull_request()

    result = sync_service.sync_repository_pull_requests(
        owner="django",
        repository="django",
        max_pages=1,
    )

    github_client.get_pull_requests.assert_called_once()
    assert result.total_processed == 1


def test_sync_recent_pull_requests_prevents_duplicates(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Use bulk lookup and update instead of creating duplicate records."""
    existing = _build_existing_pull_request()

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.return_value = _build_paginated_response(
        [GITHUB_PULL_REQUEST],
        current_page=1,
        has_next=False,
    )
    pull_request_repository.find_by_github_ids.return_value = {1001: existing}
    pull_request_repository.update.return_value = existing

    result = sync_service.sync_recent_pull_requests(owner="django", repository="django")

    pull_request_repository.create.assert_not_called()
    pull_request_repository.update.assert_called_once()
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_recent_pull_requests_raises_when_repository_not_registered(
    sync_service: PullRequestSyncService,
    repository_repository: MagicMock,
    github_client: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Raise RepositoryNotFound when the repository is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = None

    with pytest.raises(RepositoryNotFound):
        sync_service.sync_recent_pull_requests(owner="django", repository="missing")

    github_client.get_pull_requests.assert_not_called()
    pull_request_repository.create.assert_not_called()
    pull_request_repository.update.assert_not_called()


def test_sync_recent_pull_requests_raises_repository_not_found_from_github(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Propagate RepositoryNotFound from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.side_effect = RepositoryNotFound(
        "Repository django/missing was not found.",
    )

    with pytest.raises(RepositoryNotFound):
        sync_service.sync_recent_pull_requests(owner="django", repository="missing")

    pull_request_repository.create.assert_not_called()
    pull_request_repository.update.assert_not_called()


def test_sync_recent_pull_requests_raises_authentication_error(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Propagate AuthenticationError from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.side_effect = AuthenticationError(
        "GitHub authentication failed.",
    )

    with pytest.raises(AuthenticationError):
        sync_service.sync_recent_pull_requests(owner="django", repository="django")

    pull_request_repository.create.assert_not_called()
    pull_request_repository.update.assert_not_called()


def test_sync_recent_pull_requests_raises_rate_limit_exceeded(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Propagate RateLimitExceeded from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    github_client.get_pull_requests.side_effect = RateLimitExceeded(
        "GitHub rate limit exceeded.",
        remaining=0,
        reset_at=1_700_000_000,
    )

    with pytest.raises(RateLimitExceeded):
        sync_service.sync_recent_pull_requests(owner="django", repository="django")

    pull_request_repository.create.assert_not_called()
    pull_request_repository.update.assert_not_called()


def test_sync_recent_pull_requests_raises_unexpected_github_response(
    sync_service: PullRequestSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
) -> None:
    """Propagate UnexpectedGitHubResponse from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    response = GitHubResponseInfo(
        status_code=500,
        url="https://api.github.com/repos/django/django/pulls",
        body="Internal Server Error",
        headers={},
    )
    github_client.get_pull_requests.side_effect = UnexpectedGitHubResponse(
        "Unexpected GitHub response.",
        response=response,
    )

    with pytest.raises(UnexpectedGitHubResponse) as exc_info:
        sync_service.sync_recent_pull_requests(owner="django", repository="django")

    assert exc_info.value.status_code == 500
    pull_request_repository.create.assert_not_called()
    pull_request_repository.update.assert_not_called()
