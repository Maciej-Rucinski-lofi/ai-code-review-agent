"""Persistence layer for ReviewComment ORM entities."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.review_comment import ReviewComment


class ReviewCommentRepository:
    """SQLAlchemy-backed persistence for GitHub review comment records."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self._session = session

    def find_by_github_id(self, github_id: int) -> ReviewComment | None:
        """Return a review comment by its GitHub identifier, if present."""
        statement = select(ReviewComment).where(ReviewComment.github_id == github_id)
        return self._session.scalars(statement).first()

    def find_by_review(self, review_id: int) -> list[ReviewComment]:
        """Return all review comments associated with a review."""
        statement = select(ReviewComment).where(ReviewComment.review_id == review_id)
        return list(self._session.scalars(statement).all())

    def find_by_github_ids(self, github_ids: list[int]) -> dict[int, ReviewComment]:
        """Return existing review comments keyed by GitHub identifier."""
        if not github_ids:
            return {}

        statement = select(ReviewComment).where(ReviewComment.github_id.in_(github_ids))
        records = self._session.scalars(statement).all()
        return {record.github_id: record for record in records}

    def create(
        self,
        *,
        github_id: int,
        review_id: int,
        pull_request_id: int,
        body: str,
        file_path: str,
        line_number: int | None,
        created_at: datetime,
    ) -> ReviewComment:
        """Insert a new review comment record and return the persisted entity."""
        comment = ReviewComment(
            github_id=github_id,
            review_id=review_id,
            pull_request_id=pull_request_id,
            body=body,
            file_path=file_path,
            line_number=line_number,
            created_at=created_at,
        )
        self._session.add(comment)
        self._session.flush()
        return comment

    def update(
        self,
        comment: ReviewComment,
        *,
        github_id: int,
        review_id: int,
        pull_request_id: int,
        body: str,
        file_path: str,
        line_number: int | None,
        created_at: datetime,
    ) -> ReviewComment:
        """Update review comment metadata without changing the internal identifier."""
        comment.github_id = github_id
        comment.review_id = review_id
        comment.pull_request_id = pull_request_id
        comment.body = body
        comment.file_path = file_path
        comment.line_number = line_number
        comment.created_at = created_at
        self._session.flush()
        return comment
