"""Tests for pull request persistence layer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.database.models.pull_request import PullRequest

CREATED_AT = datetime(2024, 1, 1, tzinfo=UTC)
UPDATED_AT = datetime(2024, 1, 2, tzinfo=UTC)
MERGED_AT = datetime(2024, 1, 3, tzinfo=UTC)


@pytest.fixture
def session() -> MagicMock:
    """Return a mocked SQLAlchemy session."""
    return MagicMock(spec=Session)


@pytest.fixture
def pull_request_repository(session: MagicMock) -> PullRequestRepository:
    """Return a repository backed by a mocked session."""
    return PullRequestRepository(session=session)


def test_find_by_github_id_returns_pull_request(
    pull_request_repository: PullRequestRepository,
    session: MagicMock,
) -> None:
    """Return the pull request returned by the database query."""
    expected = PullRequest(
        github_id=1001,
        repository_id=1,
        number=42,
        title="Fix bug",
        body=None,
        state="closed",
        author_login="alice",
        merged_at=MERGED_AT,
    )
    scalars = session.scalars.return_value
    scalars.first.return_value = expected

    result = pull_request_repository.find_by_github_id(1001)

    session.scalars.assert_called_once()
    assert result is expected


def test_find_by_repository_and_number_returns_pull_request(
    pull_request_repository: PullRequestRepository,
    session: MagicMock,
) -> None:
    """Return the pull request matched by repository and number."""
    expected = PullRequest(
        github_id=1001,
        repository_id=1,
        number=42,
        title="Fix bug",
        body=None,
        state="closed",
        author_login="alice",
        merged_at=MERGED_AT,
    )
    scalars = session.scalars.return_value
    scalars.first.return_value = expected

    result = pull_request_repository.find_by_repository_and_number(1, 42)

    session.scalars.assert_called_once()
    assert result is expected


def test_find_by_github_ids_returns_empty_dict_for_empty_input(
    pull_request_repository: PullRequestRepository,
    session: MagicMock,
) -> None:
    """Skip database access when no GitHub identifiers are provided."""
    result = pull_request_repository.find_by_github_ids([])

    session.scalars.assert_not_called()
    assert result == {}


def test_find_by_repository_id_returns_pull_requests(
    pull_request_repository: PullRequestRepository,
    session: MagicMock,
) -> None:
    """Return pull requests for a repository with optional limit."""
    first = PullRequest(
        github_id=1001,
        repository_id=1,
        number=42,
        title="First",
        body=None,
        state="closed",
        author_login="alice",
        merged_at=MERGED_AT,
    )
    second = PullRequest(
        github_id=1002,
        repository_id=1,
        number=43,
        title="Second",
        body=None,
        state="open",
        author_login="bob",
        merged_at=None,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = pull_request_repository.find_by_repository_id(1, limit=10)

    session.scalars.assert_called_once()
    assert result == [first, second]


def test_find_by_github_ids_returns_records_keyed_by_github_id(
    pull_request_repository: PullRequestRepository,
    session: MagicMock,
) -> None:
    """Return existing pull requests keyed by GitHub identifier."""
    first = PullRequest(
        github_id=1001,
        repository_id=1,
        number=42,
        title="First",
        body=None,
        state="closed",
        author_login="alice",
        merged_at=MERGED_AT,
    )
    second = PullRequest(
        github_id=1002,
        repository_id=1,
        number=43,
        title="Second",
        body=None,
        state="open",
        author_login="bob",
        merged_at=None,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = pull_request_repository.find_by_github_ids([1001, 1002])

    session.scalars.assert_called_once()
    assert result == {1001: first, 1002: second}


def test_create_persists_pull_request(
    pull_request_repository: PullRequestRepository,
    session: MagicMock,
) -> None:
    """Add and flush a new pull request record."""
    result = pull_request_repository.create(
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

    session.add.assert_called_once()
    session.flush.assert_called_once()
    added_pull_request = session.add.call_args.args[0]
    assert added_pull_request.github_id == 1001
    assert added_pull_request.repository_id == 1
    assert added_pull_request.number == 42
    assert added_pull_request.title == "Fix bug"
    assert added_pull_request.body == "Description"
    assert added_pull_request.state == "closed"
    assert added_pull_request.author_login == "alice"
    assert added_pull_request.created_at == CREATED_AT
    assert added_pull_request.updated_at == UPDATED_AT
    assert added_pull_request.merged_at == MERGED_AT
    assert result is added_pull_request


def test_update_persists_metadata_without_changing_id(
    pull_request_repository: PullRequestRepository,
    session: MagicMock,
) -> None:
    """Update tracked fields while preserving the internal identifier."""
    existing = PullRequest(
        github_id=1000,
        repository_id=1,
        number=41,
        title="Old title",
        body="Old body",
        state="open",
        author_login="old-user",
        merged_at=None,
    )
    existing.id = 99

    result = pull_request_repository.update(
        existing,
        github_id=1001,
        repository_id=1,
        number=42,
        title="Updated title",
        body="Updated body",
        state="closed",
        author_login="alice",
        created_at=CREATED_AT,
        updated_at=UPDATED_AT,
        merged_at=MERGED_AT,
    )

    session.flush.assert_called_once()
    assert existing.id == 99
    assert existing.github_id == 1001
    assert existing.number == 42
    assert existing.title == "Updated title"
    assert existing.body == "Updated body"
    assert existing.state == "closed"
    assert existing.author_login == "alice"
    assert existing.created_at == CREATED_AT
    assert existing.updated_at == UPDATED_AT
    assert existing.merged_at == MERGED_AT
    assert result is existing
