"""Tests for review comment persistence layer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.collector.repositories.review_comment_repository import ReviewCommentRepository
from app.database.models.review_comment import ReviewComment

CREATED_AT = datetime(2024, 1, 2, 7, 30, tzinfo=UTC)


@pytest.fixture
def session() -> MagicMock:
    """Return a mocked SQLAlchemy session."""
    return MagicMock(spec=Session)


@pytest.fixture
def review_comment_repository(session: MagicMock) -> ReviewCommentRepository:
    """Return a repository backed by a mocked session."""
    return ReviewCommentRepository(session=session)


def test_find_by_github_id_returns_comment(
    review_comment_repository: ReviewCommentRepository,
    session: MagicMock,
) -> None:
    """Return the review comment returned by the database query."""
    expected = ReviewComment(
        github_id=1011,
        review_id=20,
        pull_request_id=10,
        body="Consider renaming this variable.",
        file_path="django/db/models/query.py",
        line_number=12,
        created_at=CREATED_AT,
    )
    scalars = session.scalars.return_value
    scalars.first.return_value = expected

    result = review_comment_repository.find_by_github_id(1011)

    session.scalars.assert_called_once()
    assert result is expected


def test_find_by_review_returns_comments(
    review_comment_repository: ReviewCommentRepository,
    session: MagicMock,
) -> None:
    """Return all review comments associated with a review."""
    first = ReviewComment(
        github_id=1011,
        review_id=20,
        pull_request_id=10,
        body="First comment",
        file_path="django/db/models/query.py",
        line_number=12,
        created_at=CREATED_AT,
    )
    second = ReviewComment(
        github_id=1012,
        review_id=20,
        pull_request_id=10,
        body="Second comment",
        file_path="django/db/models/base.py",
        line_number=5,
        created_at=CREATED_AT,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = review_comment_repository.find_by_review(20)

    session.scalars.assert_called_once()
    assert result == [first, second]


def test_find_by_github_ids_returns_empty_dict_for_empty_input(
    review_comment_repository: ReviewCommentRepository,
    session: MagicMock,
) -> None:
    """Skip database access when no GitHub identifiers are provided."""
    result = review_comment_repository.find_by_github_ids([])

    session.scalars.assert_not_called()
    assert result == {}


def test_find_by_github_ids_returns_records_keyed_by_github_id(
    review_comment_repository: ReviewCommentRepository,
    session: MagicMock,
) -> None:
    """Return existing review comments keyed by GitHub identifier."""
    first = ReviewComment(
        github_id=1011,
        review_id=20,
        pull_request_id=10,
        body="First comment",
        file_path="django/db/models/query.py",
        line_number=12,
        created_at=CREATED_AT,
    )
    second = ReviewComment(
        github_id=1012,
        review_id=20,
        pull_request_id=10,
        body="Second comment",
        file_path="django/db/models/base.py",
        line_number=5,
        created_at=CREATED_AT,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = review_comment_repository.find_by_github_ids([1011, 1012])

    session.scalars.assert_called_once()
    assert result == {1011: first, 1012: second}


def test_create_persists_review_comment(
    review_comment_repository: ReviewCommentRepository,
    session: MagicMock,
) -> None:
    """Add and flush a new review comment record."""
    result = review_comment_repository.create(
        github_id=1011,
        review_id=20,
        pull_request_id=10,
        body="Consider renaming this variable.",
        file_path="django/db/models/query.py",
        line_number=12,
        created_at=CREATED_AT,
    )

    session.add.assert_called_once()
    session.flush.assert_called_once()
    added_comment = session.add.call_args.args[0]
    assert added_comment.github_id == 1011
    assert added_comment.review_id == 20
    assert added_comment.pull_request_id == 10
    assert added_comment.body == "Consider renaming this variable."
    assert added_comment.file_path == "django/db/models/query.py"
    assert added_comment.line_number == 12
    assert added_comment.created_at == CREATED_AT
    assert result is added_comment


def test_update_persists_metadata_without_changing_id(
    review_comment_repository: ReviewCommentRepository,
    session: MagicMock,
) -> None:
    """Update tracked fields while preserving the internal identifier."""
    existing = ReviewComment(
        github_id=1010,
        review_id=20,
        pull_request_id=10,
        body="Old body",
        file_path="old/path.py",
        line_number=1,
        created_at=CREATED_AT,
    )
    existing.id = 99
    updated_at = datetime(2024, 2, 1, tzinfo=UTC)

    result = review_comment_repository.update(
        existing,
        github_id=1011,
        review_id=21,
        pull_request_id=11,
        body="Updated body",
        file_path="django/db/models/query.py",
        line_number=12,
        created_at=updated_at,
    )

    session.flush.assert_called_once()
    assert existing.id == 99
    assert existing.github_id == 1011
    assert existing.review_id == 21
    assert existing.pull_request_id == 11
    assert existing.body == "Updated body"
    assert existing.file_path == "django/db/models/query.py"
    assert existing.line_number == 12
    assert existing.created_at == updated_at
    assert result is existing
