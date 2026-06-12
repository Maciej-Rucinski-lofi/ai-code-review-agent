"""Persistence layer for Repository ORM entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.repository import Repository


class RepositoryRepository:
    """SQLAlchemy-backed persistence for GitHub repository records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self._session = session

    def find_by_github_id(self, github_id: int) -> Repository | None:
        """Return a repository by its GitHub identifier, if present."""
        statement = select(Repository).where(Repository.github_id == github_id)
        return self._session.scalars(statement).first()

    def find_by_owner_and_name(self, owner: str, name: str) -> Repository | None:
        """Return a repository by owner and name, if present."""
        statement = select(Repository).where(
            Repository.owner == owner,
            Repository.name == name,
        )
        return self._session.scalars(statement).first()

    def create(
        self,
        *,
        github_id: int,
        owner: str,
        name: str,
        description: str | None,
        default_branch: str,
    ) -> Repository:
        """Insert a new repository record and return the persisted entity."""
        repository = Repository(
            github_id=github_id,
            owner=owner,
            name=name,
            description=description,
            default_branch=default_branch,
        )
        self._session.add(repository)
        self._session.flush()
        return repository

    def update(
        self,
        repository: Repository,
        *,
        github_id: int,
        owner: str,
        name: str,
        description: str | None,
        default_branch: str,
    ) -> Repository:
        """Update repository metadata without changing the internal identifier."""
        repository.github_id = github_id
        repository.owner = owner
        repository.name = name
        repository.description = description
        repository.default_branch = default_branch
        self._session.flush()
        return repository
