"""PullRequest ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.analysis import Analysis
    from app.database.models.file_change import FileChange
    from app.database.models.repository import Repository
    from app.database.models.review import Review
    from app.database.models.review_comment import ReviewComment


class PullRequest(Base, TimestampMixin):
    """GitHub pull request with metadata and review associations."""

    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "number"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    repository_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("repositories.id"),
        index=True,
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    author_login: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    repository: Mapped["Repository"] = relationship(back_populates="pull_requests")
    file_changes: Mapped[list["FileChange"]] = relationship(
        back_populates="pull_request"
    )
    reviews: Mapped[list["Review"]] = relationship(back_populates="pull_request")
    review_comments: Mapped[list["ReviewComment"]] = relationship(
        back_populates="pull_request",
    )
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="pull_request")
