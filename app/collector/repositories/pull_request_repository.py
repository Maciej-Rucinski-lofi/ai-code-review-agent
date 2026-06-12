"""Persistence layer for PullRequest ORM entities."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.pull_request import PullRequest


class PullRequestRepository:
    """SQLAlchemy-backed persistence for GitHub pull request records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self._session = session

    def find_by_github_id(self, github_id: int) -> PullRequest | None:
        """Return a pull request by its GitHub identifier, if present."""
        statement = select(PullRequest).where(PullRequest.github_id == github_id)
        return self._session.scalars(statement).first()

    def find_by_repository_and_number(
        self,
        repository_id: int,
        number: int,
    ) -> PullRequest | None:
        """Return a pull request by repository and number, if present."""
        statement = select(PullRequest).where(
            PullRequest.repository_id == repository_id,
            PullRequest.number == number,
        )
        return self._session.scalars(statement).first()

    def find_by_github_ids(self, github_ids: list[int]) -> dict[int, PullRequest]:
        """Return existing pull requests keyed by GitHub identifier."""
        if not github_ids:
            return {}

        statement = select(PullRequest).where(PullRequest.github_id.in_(github_ids))
        records = self._session.scalars(statement).all()
        return {record.github_id: record for record in records}

    def create(
        self,
        *,
        github_id: int,
        repository_id: int,
        number: int,
        title: str,
        body: str | None,
        state: str,
        author_login: str,
        created_at: datetime,
        updated_at: datetime,
        merged_at: datetime | None,
    ) -> PullRequest:
        """Insert a new pull request record and return the persisted entity."""
        pull_request = PullRequest(
            github_id=github_id,
            repository_id=repository_id,
            number=number,
            title=title,
            body=body,
            state=state,
            author_login=author_login,
            created_at=created_at,
            updated_at=updated_at,
            merged_at=merged_at,
        )
        self._session.add(pull_request)
        self._session.flush()
        return pull_request

    def update(
        self,
        pull_request: PullRequest,
        *,
        github_id: int,
        repository_id: int,
        number: int,
        title: str,
        body: str | None,
        state: str,
        author_login: str,
        created_at: datetime,
        updated_at: datetime,
        merged_at: datetime | None,
    ) -> PullRequest:
        """Update pull request metadata without changing the internal identifier."""
        pull_request.github_id = github_id
        pull_request.repository_id = repository_id
        pull_request.number = number
        pull_request.title = title
        pull_request.body = body
        pull_request.state = state
        pull_request.author_login = author_login
        pull_request.created_at = created_at
        pull_request.updated_at = updated_at
        pull_request.merged_at = merged_at
        self._session.flush()
        return pull_request
