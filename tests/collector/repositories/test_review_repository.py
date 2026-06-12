"""Tests for review persistence layer."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.collector.repositories.review_repository import ReviewRepository
from app.database.models.review import Review

SUBMITTED_AT = datetime(2024, 1, 10, tzinfo=UTC)


@pytest.fixture
def session() -> MagicMock:
    """Return a mocked SQLAlchemy session."""
    return MagicMock(spec=Session)


@pytest.fixture
def review_repository(session: MagicMock) -> ReviewRepository:
    """Return a repository backed by a mocked session."""
    return ReviewRepository(session=session)


def test_find_by_github_id_returns_review(
    review_repository: ReviewRepository,
    session: MagicMock,
) -> None:
    """Return the review returned by the database query."""
    expected = Review(
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="APPROVED",
        submitted_at=SUBMITTED_AT,
    )
    scalars = session.scalars.return_value
    scalars.first.return_value = expected

    result = review_repository.find_by_github_id(5001)

    session.scalars.assert_called_once()
    assert result is expected


def test_find_by_pull_request_returns_reviews(
    review_repository: ReviewRepository,
    session: MagicMock,
) -> None:
    """Return all reviews associated with a pull request."""
    first = Review(
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="APPROVED",
        submitted_at=SUBMITTED_AT,
    )
    second = Review(
        github_id=5002,
        pull_request_id=10,
        reviewer_login="bob",
        state="COMMENTED",
        submitted_at=SUBMITTED_AT,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = review_repository.find_by_pull_request(10)

    session.scalars.assert_called_once()
    assert result == [first, second]


def test_find_by_github_ids_returns_empty_dict_for_empty_input(
    review_repository: ReviewRepository,
    session: MagicMock,
) -> None:
    """Skip database access when no GitHub identifiers are provided."""
    result = review_repository.find_by_github_ids([])

    session.scalars.assert_not_called()
    assert result == {}


def test_find_by_github_ids_returns_records_keyed_by_github_id(
    review_repository: ReviewRepository,
    session: MagicMock,
) -> None:
    """Return existing reviews keyed by GitHub identifier."""
    first = Review(
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="APPROVED",
        submitted_at=SUBMITTED_AT,
    )
    second = Review(
        github_id=5002,
        pull_request_id=10,
        reviewer_login="bob",
        state="CHANGES_REQUESTED",
        submitted_at=SUBMITTED_AT,
    )
    scalars = session.scalars.return_value
    scalars.all.return_value = [first, second]

    result = review_repository.find_by_github_ids([5001, 5002])

    session.scalars.assert_called_once()
    assert result == {5001: first, 5002: second}


def test_create_persists_review(
    review_repository: ReviewRepository,
    session: MagicMock,
) -> None:
    """Add and flush a new review record."""
    result = review_repository.create(
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="APPROVED",
        submitted_at=SUBMITTED_AT,
    )

    session.add.assert_called_once()
    session.flush.assert_called_once()
    added_review = session.add.call_args.args[0]
    assert added_review.github_id == 5001
    assert added_review.pull_request_id == 10
    assert added_review.reviewer_login == "alice"
    assert added_review.state == "APPROVED"
    assert added_review.submitted_at == SUBMITTED_AT
    assert result is added_review


def test_update_persists_metadata_without_changing_id(
    review_repository: ReviewRepository,
    session: MagicMock,
) -> None:
    """Update tracked fields while preserving the internal identifier."""
    existing = Review(
        github_id=5000,
        pull_request_id=10,
        reviewer_login="old-user",
        state="COMMENTED",
        submitted_at=SUBMITTED_AT,
    )
    existing.id = 99

    result = review_repository.update(
        existing,
        github_id=5001,
        pull_request_id=10,
        reviewer_login="alice",
        state="APPROVED",
        submitted_at=datetime(2024, 2, 1, tzinfo=UTC),
    )

    session.flush.assert_called_once()
    assert existing.id == 99
    assert existing.github_id == 5001
    assert existing.reviewer_login == "alice"
    assert existing.state == "APPROVED"
    assert existing.submitted_at == datetime(2024, 2, 1, tzinfo=UTC)
    assert result is existing
