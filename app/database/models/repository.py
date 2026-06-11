"""Repository ORM model."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.database.models.pull_request import PullRequest


class Repository(Base, TimestampMixin):
    """GitHub repository persisted for pull request collection."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False)

    pull_requests: Mapped[list["PullRequest"]] = relationship(
        back_populates="repository",
    )
