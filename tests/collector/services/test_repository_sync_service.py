"""Tests for repository synchronization service."""

from __future__ import annotations

from datetime import UTC
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
from app.collector.github.models import Repository as GitHubRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.schemas.repository_sync_result import RepositorySyncAction
from app.collector.services.repository_sync_service import RepositorySyncService
from app.database.models.repository import Repository

GITHUB_REPOSITORY = GitHubRepository(
    github_id=123,
    owner="django",
    name="django",
    full_name="django/django",
    description="The Web framework for perfectionists with deadlines.",
    default_branch="main",
    html_url="https://github.com/django/django",
)

UPDATED_GITHUB_REPOSITORY = GitHubRepository(
    github_id=123,
    owner="django",
    name="django",
    full_name="django/django",
    description="Updated description.",
    default_branch="stable",
    html_url="https://github.com/django/django",
)


def _build_existing_repository(
    *,
    repository_id: int = 1,
    github_id: int = 123,
    owner: str = "django",
    name: str = "django",
    description: str | None = "Old description.",
    default_branch: str = "main",
) -> Repository:
    repository = Repository(
        github_id=github_id,
        owner=owner,
        name=name,
        description=description,
        default_branch=default_branch,
    )
    repository.id = repository_id
    return repository


@pytest.fixture
def github_client() -> MagicMock:
    """Return a mocked GitHub client."""
    return create_autospec(GitHubClient, instance=True)


@pytest.fixture
def repository_repository() -> MagicMock:
    """Return a mocked repository persistence layer."""
    return create_autospec(RepositoryRepository, instance=True)


@pytest.fixture
def sync_service(
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> RepositorySyncService:
    """Return a sync service with mocked dependencies."""
    return RepositorySyncService(
        github_client=github_client,
        repository_repository=repository_repository,
    )


def test_sync_repository_creates_new_record(
    sync_service: RepositorySyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> None:
    """Create a repository when no local record exists."""
    github_client.get_repository.return_value = GITHUB_REPOSITORY
    repository_repository.find_by_github_id.return_value = None
    repository_repository.find_by_owner_and_name.return_value = None
    repository_repository.create.return_value = _build_existing_repository()

    result = sync_service.sync_repository(owner="django", repository="django")

    github_client.get_repository.assert_called_once_with("django", "django")
    repository_repository.find_by_github_id.assert_called_once_with(123)
    repository_repository.find_by_owner_and_name.assert_called_once_with(
        "django",
        "django",
    )
    repository_repository.create.assert_called_once_with(
        github_id=123,
        owner="django",
        name="django",
        description=GITHUB_REPOSITORY.description,
        default_branch="main",
    )
    repository_repository.update.assert_not_called()
    assert result.repository_id == 1
    assert result.github_id == 123
    assert result.action is RepositorySyncAction.CREATED
    assert result.synchronized_at.tzinfo is UTC


def test_sync_repository_updates_existing_record_by_github_id(
    sync_service: RepositorySyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> None:
    """Update an existing repository when it is found by GitHub ID."""
    existing = _build_existing_repository()
    updated = _build_existing_repository(
        description=UPDATED_GITHUB_REPOSITORY.description,
        default_branch="stable",
    )

    github_client.get_repository.return_value = UPDATED_GITHUB_REPOSITORY
    repository_repository.find_by_github_id.return_value = existing
    repository_repository.update.return_value = updated

    result = sync_service.sync_repository(owner="django", repository="django")

    repository_repository.find_by_github_id.assert_called_once_with(123)
    repository_repository.find_by_owner_and_name.assert_not_called()
    repository_repository.create.assert_not_called()
    repository_repository.update.assert_called_once_with(
        existing,
        github_id=123,
        owner="django",
        name="django",
        description="Updated description.",
        default_branch="stable",
    )
    assert result.repository_id == 1
    assert result.github_id == 123
    assert result.action is RepositorySyncAction.UPDATED


def test_sync_repository_updates_existing_record_by_owner_and_name(
    sync_service: RepositorySyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> None:
    """Fall back to owner/name lookup when GitHub ID lookup misses."""
    existing = _build_existing_repository()
    updated = _build_existing_repository(
        description=UPDATED_GITHUB_REPOSITORY.description,
        default_branch="stable",
    )

    github_client.get_repository.return_value = UPDATED_GITHUB_REPOSITORY
    repository_repository.find_by_github_id.return_value = None
    repository_repository.find_by_owner_and_name.return_value = existing
    repository_repository.update.return_value = updated

    result = sync_service.sync_repository(owner="django", repository="django")

    repository_repository.find_by_owner_and_name.assert_called_once_with(
        "django",
        "django",
    )
    repository_repository.update.assert_called_once()
    assert result.action is RepositorySyncAction.UPDATED


def test_sync_repository_raises_repository_not_found(
    sync_service: RepositorySyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> None:
    """Propagate RepositoryNotFound from the GitHub client."""
    github_client.get_repository.side_effect = RepositoryNotFound(
        "Repository django/missing was not found.",
    )

    with pytest.raises(RepositoryNotFound):
        sync_service.sync_repository(owner="django", repository="missing")

    repository_repository.create.assert_not_called()
    repository_repository.update.assert_not_called()


def test_sync_repository_raises_authentication_error(
    sync_service: RepositorySyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> None:
    """Propagate AuthenticationError from the GitHub client."""
    github_client.get_repository.side_effect = AuthenticationError(
        "GitHub authentication failed.",
    )

    with pytest.raises(AuthenticationError):
        sync_service.sync_repository(owner="django", repository="django")

    repository_repository.create.assert_not_called()
    repository_repository.update.assert_not_called()


def test_sync_repository_raises_rate_limit_exceeded(
    sync_service: RepositorySyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> None:
    """Propagate RateLimitExceeded from the GitHub client."""
    github_client.get_repository.side_effect = RateLimitExceeded(
        "GitHub rate limit exceeded.",
        remaining=0,
        reset_at=1_700_000_000,
    )

    with pytest.raises(RateLimitExceeded):
        sync_service.sync_repository(owner="django", repository="django")

    repository_repository.create.assert_not_called()
    repository_repository.update.assert_not_called()


def test_sync_repository_raises_unexpected_github_response(
    sync_service: RepositorySyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
) -> None:
    """Propagate UnexpectedGitHubResponse from the GitHub client."""
    response = GitHubResponseInfo(
        status_code=500,
        url="https://api.github.com/repos/django/django",
        body="Internal Server Error",
        headers={},
    )
    github_client.get_repository.side_effect = UnexpectedGitHubResponse(
        "Unexpected GitHub response.",
        response=response,
    )

    with pytest.raises(UnexpectedGitHubResponse) as exc_info:
        sync_service.sync_repository(owner="django", repository="django")

    assert exc_info.value.status_code == 500
    repository_repository.create.assert_not_called()
    repository_repository.update.assert_not_called()
