"""Persistence layer for Review ORM entities."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.review import Review


class ReviewRepository:
    """SQLAlchemy-backed persistence for GitHub review records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self._session = session

    def find_by_github_id(self, github_id: int) -> Review | None:
        """Return a review by its GitHub identifier, if present."""
        statement = select(Review).where(Review.github_id == github_id)
        return self._session.scalars(statement).first()

    def find_by_pull_request(self, pull_request_id: int) -> list[Review]:
        """Return all reviews associated with a pull request."""
        statement = select(Review).where(Review.pull_request_id == pull_request_id)
        return list(self._session.scalars(statement).all())

    def find_by_github_ids(self, github_ids: list[int]) -> dict[int, Review]:
        """Return existing reviews keyed by GitHub identifier."""
        if not github_ids:
            return {}

        statement = select(Review).where(Review.github_id.in_(github_ids))
        records = self._session.scalars(statement).all()
        return {record.github_id: record for record in records}

    def create(
        self,
        *,
        github_id: int,
        pull_request_id: int,
        reviewer_login: str,
        state: str,
        submitted_at: datetime,
    ) -> Review:
        """Insert a new review record and return the persisted entity."""
        review = Review(
            github_id=github_id,
            pull_request_id=pull_request_id,
            reviewer_login=reviewer_login,
            state=state,
            submitted_at=submitted_at,
        )
        self._session.add(review)
        self._session.flush()
        return review

    def update(
        self,
        review: Review,
        *,
        github_id: int,
        pull_request_id: int,
        reviewer_login: str,
        state: str,
        submitted_at: datetime,
    ) -> Review:
        """Update review metadata without changing the internal identifier."""
        review.github_id = github_id
        review.pull_request_id = pull_request_id
        review.reviewer_login = reviewer_login
        review.state = state
        review.submitted_at = submitted_at
        self._session.flush()
        return review
