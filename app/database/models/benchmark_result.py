"""BenchmarkResult ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.analysis import Analysis


class BenchmarkResult(Base):
    """Benchmark metrics comparing AI findings against human review comments."""

    __tablename__ = "benchmark_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("analyses.id"),
        index=True,
        nullable=False,
    )
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    match_rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    analysis: Mapped["Analysis"] = relationship(back_populates="benchmark_results")
