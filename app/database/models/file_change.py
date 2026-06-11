"""FileChange ORM model."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.pull_request import PullRequest


class FileChange(Base):
    """Single file diff within a pull request."""

    __tablename__ = "file_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pull_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pull_requests.id"),
        index=True,
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    additions: Mapped[int] = mapped_column(Integer, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, nullable=False)
    changes: Mapped[int] = mapped_column(Integer, nullable=False)
    patch: Mapped[str | None] = mapped_column(Text, nullable=True)

    pull_request: Mapped["PullRequest"] = relationship(back_populates="file_changes")
