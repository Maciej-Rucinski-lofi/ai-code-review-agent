"""Tests for file change synchronization service."""

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
from app.collector.github.models import FileChange as GitHubFileChange
from app.collector.repositories.file_change_repository import FileChangeRepository
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.services.file_change_sync_service import FileChangeSyncService
from app.database.models.file_change import FileChange
from app.database.models.pull_request import PullRequest
from app.database.models.repository import Repository

PATCH = (
    "@@ -1,3 +1,4 @@\n"
    " def authenticate():\n"
    "-    pass\n"
    "+    return True\n"
)

LARGE_PATCH = PATCH + ("\n+    # additional context line\n" * 5000)

GITHUB_FILE = GitHubFileChange(
    filename="auth.py",
    status="modified",
    additions=1,
    deletions=1,
    changes=2,
    patch=PATCH,
    previous_filename=None,
)

UPDATED_GITHUB_FILE = GitHubFileChange(
    filename="auth.py",
    status="modified",
    additions=2,
    deletions=3,
    changes=5,
    patch=LARGE_PATCH,
    previous_filename=None,
)

SECOND_GITHUB_FILE = GitHubFileChange(
    filename="models/user.py",
    status="added",
    additions=5,
    deletions=0,
    changes=5,
    patch=None,
    previous_filename=None,
)

GO_FILE = GitHubFileChange(
    filename="internal/service/payment.go",
    status="modified",
    additions=10,
    deletions=2,
    changes=12,
    patch="@@ -1,1 +1,2 @@\n package payment\n",
    previous_filename=None,
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


def _build_existing_file_change(
    *,
    file_change_id: int = 30,
    filename: str = "auth.py",
    patch: str | None = PATCH,
) -> FileChange:
    file_change = FileChange(
        pull_request_id=10,
        filename=filename,
        additions=1,
        deletions=1,
        changes=2,
        patch=patch,
    )
    file_change.id = file_change_id
    return file_change


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
def file_change_repository() -> MagicMock:
    """Return a mocked file change persistence layer."""
    return create_autospec(FileChangeRepository, instance=True)


@pytest.fixture
def sync_service(
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> FileChangeSyncService:
    """Return a sync service with mocked dependencies."""
    return FileChangeSyncService(
        github_client=github_client,
        repository_repository=repository_repository,
        pull_request_repository=pull_request_repository,
        file_change_repository=file_change_repository,
    )


def test_sync_pull_request_files_creates_new_records(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Create file changes when no local records exist."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.return_value = [GITHUB_FILE]
    file_change_repository.find_by_pull_request_and_filenames.return_value = {}
    file_change_repository.find_by_pull_request_id.return_value = []
    file_change_repository.create.return_value = _build_existing_file_change()

    result = sync_service.sync_pull_request_files(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    github_client.get_pull_request_files.assert_called_once_with(
        "django",
        "django",
        42,
    )
    file_change_repository.find_by_pull_request_and_filenames.assert_called_once_with(
        10,
        ["auth.py"],
    )
    file_change_repository.create.assert_called_once_with(
        pull_request_id=10,
        filename="auth.py",
        additions=1,
        deletions=1,
        changes=2,
        patch=PATCH,
    )
    file_change_repository.update.assert_not_called()
    assert result.pull_request_id == 10
    assert result.total_processed == 1
    assert result.created_count == 1
    assert result.updated_count == 0
    assert result.synchronized_at.tzinfo is UTC


def test_sync_pull_request_files_updates_existing_records(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Update file changes when they already exist locally."""
    existing = _build_existing_file_change()
    updated = _build_existing_file_change()

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.return_value = [UPDATED_GITHUB_FILE]
    file_change_repository.find_by_pull_request_and_filenames.return_value = {
        "auth.py": existing,
    }
    file_change_repository.find_by_pull_request_id.return_value = [existing]
    file_change_repository.update.return_value = updated

    result = sync_service.sync_pull_request_files(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_called_once_with(
        existing,
        pull_request_id=10,
        filename="auth.py",
        additions=2,
        deletions=3,
        changes=5,
        patch=LARGE_PATCH,
    )
    assert result.total_processed == 1
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_pull_request_files_prevents_duplicates(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Use bulk lookup and update instead of creating duplicate records."""
    existing = _build_existing_file_change()

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.return_value = [GITHUB_FILE]
    file_change_repository.find_by_pull_request_and_filenames.return_value = {
        "auth.py": existing,
    }
    file_change_repository.find_by_pull_request_id.return_value = [existing]
    file_change_repository.update.return_value = existing

    result = sync_service.sync_pull_request_files(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_called_once()
    assert result.created_count == 0
    assert result.updated_count == 1


def test_sync_pull_request_files_persists_patch_without_transformation(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Store the GitHub patch exactly as returned."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.return_value = [GITHUB_FILE]
    file_change_repository.find_by_pull_request_and_filenames.return_value = {}
    file_change_repository.find_by_pull_request_id.return_value = []
    file_change_repository.create.return_value = _build_existing_file_change()

    sync_service.sync_pull_request_files(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    create_kwargs = file_change_repository.create.call_args.kwargs
    assert create_kwargs["patch"] == PATCH
    assert create_kwargs["patch"].startswith("@@ -1,3 +1,4 @@\n")
    assert "-    pass\n" in create_kwargs["patch"]
    assert "+    return True\n" in create_kwargs["patch"]


def test_sync_pull_request_files_handles_large_patch(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Persist large patch payloads without truncation."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.return_value = [UPDATED_GITHUB_FILE]
    file_change_repository.find_by_pull_request_and_filenames.return_value = {}
    file_change_repository.find_by_pull_request_id.return_value = []
    file_change_repository.create.return_value = _build_existing_file_change(
        patch=LARGE_PATCH,
    )

    sync_service.sync_pull_request_files(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    create_kwargs = file_change_repository.create.call_args.kwargs
    assert create_kwargs["patch"] == LARGE_PATCH
    assert len(create_kwargs["patch"]) > 100_000


def test_sync_pull_request_files_supports_multiple_languages(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Synchronize file changes without filtering by language."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.return_value = [
        GITHUB_FILE,
        SECOND_GITHUB_FILE,
        GO_FILE,
    ]
    file_change_repository.find_by_pull_request_and_filenames.return_value = {}
    file_change_repository.find_by_pull_request_id.return_value = []
    file_change_repository.create.side_effect = [
        _build_existing_file_change(file_change_id=30, filename="auth.py"),
        _build_existing_file_change(file_change_id=31, filename="models/user.py"),
        _build_existing_file_change(
            file_change_id=32,
            filename="internal/service/payment.go",
        ),
    ]

    result = sync_service.sync_pull_request_files(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    assert file_change_repository.create.call_count == 3
    assert result.total_processed == 3
    assert result.created_count == 3


def test_sync_pull_request_files_removes_stale_records(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Remove local file changes no longer present in the GitHub response."""
    existing = _build_existing_file_change()
    stale = _build_existing_file_change(
        file_change_id=31,
        filename="removed.py",
    )

    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.return_value = [GITHUB_FILE]
    file_change_repository.find_by_pull_request_and_filenames.return_value = {
        "auth.py": existing,
    }
    file_change_repository.find_by_pull_request_id.return_value = [existing, stale]
    file_change_repository.update.return_value = existing

    sync_service.sync_pull_request_files(
        owner="django",
        repository="django",
        pull_request_number=42,
    )

    file_change_repository.delete_by_ids.assert_called_once_with([31])


def test_sync_repository_files_processes_multiple_pull_requests(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Synchronize file changes across all registered pull requests."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_id.return_value = [
        _build_local_pull_request(pull_request_id=10, number=42),
        _build_local_pull_request(pull_request_id=11, number=43),
    ]
    github_client.get_pull_request_files.side_effect = [
        [GITHUB_FILE],
        [SECOND_GITHUB_FILE],
    ]
    file_change_repository.find_by_pull_request_and_filenames.side_effect = [{}, {}]
    file_change_repository.find_by_pull_request_id.return_value = []
    file_change_repository.create.side_effect = [
        _build_existing_file_change(),
        _build_existing_file_change(file_change_id=31, filename="models/user.py"),
    ]

    result = sync_service.sync_repository_files(owner="django", repository="django")

    pull_request_repository.find_by_repository_id.assert_called_once_with(1, limit=None)
    assert github_client.get_pull_request_files.call_count == 2
    assert result.pull_request_id is None
    assert result.total_processed == 2
    assert result.created_count == 2
    assert result.updated_count == 0


def test_sync_repository_files_respects_limit(
    sync_service: FileChangeSyncService,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    github_client: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Pass the processing limit to the pull request lookup."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_id.return_value = [
        _build_local_pull_request(),
    ]
    github_client.get_pull_request_files.return_value = []
    file_change_repository.find_by_pull_request_id.return_value = []

    sync_service.sync_repository_files(
        owner="django",
        repository="django",
        limit=5,
    )

    pull_request_repository.find_by_repository_id.assert_called_once_with(1, limit=5)


def test_sync_pull_request_files_raises_when_repository_not_registered(
    sync_service: FileChangeSyncService,
    repository_repository: MagicMock,
    github_client: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Raise RepositoryNotFound when the repository is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = None

    with pytest.raises(RepositoryNotFound):
        sync_service.sync_pull_request_files(
            owner="django",
            repository="missing",
            pull_request_number=42,
        )

    github_client.get_pull_request_files.assert_not_called()
    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_not_called()


def test_sync_pull_request_files_raises_when_pull_request_not_registered(
    sync_service: FileChangeSyncService,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    github_client: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Raise PullRequestNotFound when the pull request is missing locally."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = None

    with pytest.raises(PullRequestNotFound):
        sync_service.sync_pull_request_files(
            owner="django",
            repository="django",
            pull_request_number=999,
        )

    github_client.get_pull_request_files.assert_not_called()
    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_not_called()


def test_sync_pull_request_files_raises_pull_request_not_found_from_github(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Propagate PullRequestNotFound from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.side_effect = PullRequestNotFound(
        "Pull request not found",
    )

    with pytest.raises(PullRequestNotFound):
        sync_service.sync_pull_request_files(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_not_called()


def test_sync_pull_request_files_raises_authentication_error(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Propagate AuthenticationError from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.side_effect = AuthenticationError(
        "GitHub authentication failed.",
    )

    with pytest.raises(AuthenticationError):
        sync_service.sync_pull_request_files(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_not_called()


def test_sync_pull_request_files_raises_rate_limit_exceeded(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
) -> None:
    """Propagate RateLimitExceeded from the GitHub client."""
    repository_repository.find_by_owner_and_name.return_value = (
        _build_local_repository()
    )
    pull_request_repository.find_by_repository_and_number.return_value = (
        _build_local_pull_request()
    )
    github_client.get_pull_request_files.side_effect = RateLimitExceeded(
        "GitHub rate limit exceeded.",
        remaining=0,
        reset_at=1_700_000_000,
    )

    with pytest.raises(RateLimitExceeded):
        sync_service.sync_pull_request_files(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_not_called()


def test_sync_pull_request_files_raises_unexpected_github_response(
    sync_service: FileChangeSyncService,
    github_client: MagicMock,
    repository_repository: MagicMock,
    pull_request_repository: MagicMock,
    file_change_repository: MagicMock,
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
        url="https://api.github.com/repos/django/django/pulls/42/files",
        body="Internal Server Error",
        headers={},
    )
    github_client.get_pull_request_files.side_effect = UnexpectedGitHubResponse(
        "Unexpected GitHub response.",
        response=response,
    )

    with pytest.raises(UnexpectedGitHubResponse) as exc_info:
        sync_service.sync_pull_request_files(
            owner="django",
            repository="django",
            pull_request_number=42,
        )

    assert exc_info.value.status_code == 500
    file_change_repository.create.assert_not_called()
    file_change_repository.update.assert_not_called()
