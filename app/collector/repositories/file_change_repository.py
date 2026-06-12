"""Persistence layer for FileChange ORM entities."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database.models.file_change import FileChange


class FileChangeRepository:
    """SQLAlchemy-backed persistence for GitHub pull request file change records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self._session = session

    def find_by_pull_request_id(self, pull_request_id: int) -> list[FileChange]:
        """Return all file changes associated with a pull request."""
        statement = select(FileChange).where(
            FileChange.pull_request_id == pull_request_id,
        )
        return list(self._session.scalars(statement).all())

    def find_by_pull_request_and_filenames(
        self,
        pull_request_id: int,
        filenames: list[str],
    ) -> dict[str, FileChange]:
        """Return existing file changes keyed by filename for a pull request."""
        if not filenames:
            return {}

        statement = select(FileChange).where(
            FileChange.pull_request_id == pull_request_id,
            FileChange.filename.in_(filenames),
        )
        records = self._session.scalars(statement).all()
        return {record.filename: record for record in records}

    def create(
        self,
        *,
        pull_request_id: int,
        filename: str,
        additions: int,
        deletions: int,
        changes: int,
        patch: str | None,
    ) -> FileChange:
        """Insert a new file change record and return the persisted entity."""
        file_change = FileChange(
            pull_request_id=pull_request_id,
            filename=filename,
            additions=additions,
            deletions=deletions,
            changes=changes,
            patch=patch,
        )
        self._session.add(file_change)
        self._session.flush()
        return file_change

    def update(
        self,
        file_change: FileChange,
        *,
        pull_request_id: int,
        filename: str,
        additions: int,
        deletions: int,
        changes: int,
        patch: str | None,
    ) -> FileChange:
        """Update file change metadata without changing the internal identifier."""
        file_change.pull_request_id = pull_request_id
        file_change.filename = filename
        file_change.additions = additions
        file_change.deletions = deletions
        file_change.changes = changes
        file_change.patch = patch
        self._session.flush()
        return file_change

    def delete_by_ids(self, file_change_ids: list[int]) -> None:
        """Remove file change records by their internal identifiers."""
        if not file_change_ids:
            return

        statement = delete(FileChange).where(FileChange.id.in_(file_change_ids))
        self._session.execute(statement)
        self._session.flush()
