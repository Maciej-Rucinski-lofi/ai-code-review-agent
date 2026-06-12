"""Tests for repository persistence layer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.collector.repositories.repository_repository import RepositoryRepository
from app.database.models.repository import Repository


@pytest.fixture
def session() -> MagicMock:
    """Return a mocked SQLAlchemy session."""
    return MagicMock(spec=Session)


@pytest.fixture
def repository_repository(session: MagicMock) -> RepositoryRepository:
    """Return a repository backed by a mocked session."""
    return RepositoryRepository(session=session)


def test_find_by_github_id_returns_repository(
    repository_repository: RepositoryRepository,
    session: MagicMock,
) -> None:
    """Return the repository returned by the database query."""
    expected = Repository(
        github_id=123,
        owner="django",
        name="django",
        description=None,
        default_branch="main",
    )
    scalars = session.scalars.return_value
    scalars.first.return_value = expected

    result = repository_repository.find_by_github_id(123)

    session.scalars.assert_called_once()
    assert result is expected


def test_find_by_owner_and_name_returns_repository(
    repository_repository: RepositoryRepository,
    session: MagicMock,
) -> None:
    """Return the repository matched by owner and name."""
    expected = Repository(
        github_id=456,
        owner="golang",
        name="go",
        description=None,
        default_branch="master",
    )
    scalars = session.scalars.return_value
    scalars.first.return_value = expected

    result = repository_repository.find_by_owner_and_name("golang", "go")

    session.scalars.assert_called_once()
    assert result is expected


def test_create_persists_repository(
    repository_repository: RepositoryRepository,
    session: MagicMock,
) -> None:
    """Add and flush a new repository record."""
    result = repository_repository.create(
        github_id=123,
        owner="django",
        name="django",
        description="Django framework.",
        default_branch="main",
    )

    session.add.assert_called_once()
    session.flush.assert_called_once()
    added_repository = session.add.call_args.args[0]
    assert added_repository.github_id == 123
    assert added_repository.owner == "django"
    assert added_repository.name == "django"
    assert added_repository.description == "Django framework."
    assert added_repository.default_branch == "main"
    assert result is added_repository


def test_update_persists_metadata_without_changing_id(
    repository_repository: RepositoryRepository,
    session: MagicMock,
) -> None:
    """Update tracked fields while preserving the internal identifier."""
    existing = Repository(
        github_id=100,
        owner="old-owner",
        name="old-name",
        description="Old description.",
        default_branch="main",
    )
    existing.id = 42

    result = repository_repository.update(
        existing,
        github_id=123,
        owner="django",
        name="django",
        description="Updated description.",
        default_branch="stable",
    )

    session.flush.assert_called_once()
    assert existing.id == 42
    assert existing.github_id == 123
    assert existing.owner == "django"
    assert existing.name == "django"
    assert existing.description == "Updated description."
    assert existing.default_branch == "stable"
    assert result is existing
