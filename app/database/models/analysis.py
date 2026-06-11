"""Analysis ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.benchmark_result import BenchmarkResult
    from app.database.models.pull_request import PullRequest


class Analysis(Base):
    """AI-generated finding for a pull request."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pull_request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("pull_requests.id"),
        index=True,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    finding: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    pull_request: Mapped["PullRequest"] = relationship(back_populates="analyses")
    benchmark_results: Mapped[list["BenchmarkResult"]] = relationship(
        back_populates="analysis",
    )
