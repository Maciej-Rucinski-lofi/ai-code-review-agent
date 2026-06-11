"""Review ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.pull_request import PullRequest
    from app.database.models.review_comment import ReviewComment


class Review(Base):
    """GitHub pull request review submitted by a reviewer."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    pull_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pull_requests.id"),
        index=True,
        nullable=False,
    )
    reviewer_login: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    pull_request: Mapped["PullRequest"] = relationship(back_populates="reviews")
    comments: Mapped[list["ReviewComment"]] = relationship(back_populates="review")
