"""ReviewComment ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.pull_request import PullRequest
    from app.database.models.review import Review


class ReviewComment(Base):
    """Inline review comment on a specific file and line in a pull request."""

    __tablename__ = "review_comments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    review_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reviews.id"),
        index=True,
        nullable=False,
    )
    pull_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pull_requests.id"),
        index=True,
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    review: Mapped["Review"] = relationship(back_populates="comments")
    pull_request: Mapped["PullRequest"] = relationship(back_populates="review_comments")
