"""Tests for file change persistence layer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.collector.repositories.file_change_repository import FileChangeRepository
from app.database.models.file_change import FileChange

PATCH = (
    "@@ -1,3 +1,4 @@\n"
    " def authenticate():\n"
    "-    pass\n"
    "+    return True\n"
)


@pytest.fixture
def session() -> MagicMock:
    """Return a mocked SQLAlchemy session."""
    return MagicMock(spec=Session)


@pytest.fixture
def file_change_repository(session: MagicMock) -> FileChangeRepository:
    """Return a repository backed by a mocked session."""
    return FileChangeRepository(session=session)


def test_find_by_pull_request_id_returns_file_changes(
    file_change_repository: FileChangeRepository,
    session: MagicMock,
) -> None:
    """Return all file changes associated with a pull request."""
    first = FileChange(
        pull_request_id=10,
        filename="auth.py",
        additions=1,
        deletions=1,
        changes=2,
        patch=PATCH,
    )
    second = FileChange(
        pull_request_id=10,
        filename="models/user.py",
        additions=5,
        deletions=0,
        changes=5,
        patch=None,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = file_change_repository.find_by_pull_request_id(10)

    session.scalars.assert_called_once()
    assert result == [first, second]


def test_find_by_pull_request_and_filenames_returns_empty_dict_for_empty_input(
    file_change_repository: FileChangeRepository,
    session: MagicMock,
) -> None:
    """Skip database access when no filenames are provided."""
    result = file_change_repository.find_by_pull_request_and_filenames(10, [])

    session.scalars.assert_not_called()
    assert result == {}


def test_find_by_pull_request_and_filenames_returns_records_keyed_by_filename(
    file_change_repository: FileChangeRepository,
    session: MagicMock,
) -> None:
    """Return existing file changes keyed by filename."""
    first = FileChange(
        pull_request_id=10,
        filename="auth.py",
        additions=1,
        deletions=1,
        changes=2,
        patch=PATCH,
    )
    second = FileChange(
        pull_request_id=10,
        filename="models/user.py",
        additions=5,
        deletions=0,
        changes=5,
        patch=None,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = file_change_repository.find_by_pull_request_and_filenames(
        10,
        ["auth.py", "models/user.py"],
    )

    session.scalars.assert_called_once()
    assert result == {"auth.py": first, "models/user.py": second}


def test_create_persists_file_change(
    file_change_repository: FileChangeRepository,
    session: MagicMock,
) -> None:
    """Add and flush a new file change record."""
    result = file_change_repository.create(
        pull_request_id=10,
        filename="auth.py",
        additions=1,
        deletions=1,
        changes=2,
        patch=PATCH,
    )

    session.add.assert_called_once()
    session.flush.assert_called_once()
    added_file_change = session.add.call_args.args[0]
    assert added_file_change.pull_request_id == 10
    assert added_file_change.filename == "auth.py"
    assert added_file_change.additions == 1
    assert added_file_change.deletions == 1
    assert added_file_change.changes == 2
    assert added_file_change.patch == PATCH
    assert result is added_file_change


def test_update_persists_metadata_without_changing_id(
    file_change_repository: FileChangeRepository,
    session: MagicMock,
) -> None:
    """Update tracked fields while preserving the internal identifier."""
    existing = FileChange(
        pull_request_id=10,
        filename="auth.py",
        additions=1,
        deletions=1,
        changes=2,
        patch="old patch",
    )
    existing.id = 99
    updated_patch = PATCH

    result = file_change_repository.update(
        existing,
        pull_request_id=10,
        filename="auth.py",
        additions=2,
        deletions=3,
        changes=5,
        patch=updated_patch,
    )

    session.flush.assert_called_once()
    assert existing.id == 99
    assert existing.pull_request_id == 10
    assert existing.filename == "auth.py"
    assert existing.additions == 2
    assert existing.deletions == 3
    assert existing.changes == 5
    assert existing.patch == updated_patch
    assert result is existing


def test_delete_by_ids_skips_database_access_for_empty_input(
    file_change_repository: FileChangeRepository,
    session: MagicMock,
) -> None:
    """Skip database access when no identifiers are provided."""
    file_change_repository.delete_by_ids([])

    session.execute.assert_not_called()
    session.flush.assert_not_called()


def test_delete_by_ids_removes_records(
    file_change_repository: FileChangeRepository,
    session: MagicMock,
) -> None:
    """Execute a bulk delete for stale file change records."""
    file_change_repository.delete_by_ids([1, 2, 3])

    session.execute.assert_called_once()
    session.flush.assert_called_once()
