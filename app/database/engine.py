"""SQLAlchemy engine and session factory creation."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.config import DatabaseSettings

DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10


def create_db_engine(settings: DatabaseSettings | None = None) -> Engine:
    """Create a SQLAlchemy engine with connection pooling."""
    resolved_settings = settings or DatabaseSettings.from_env()
    return create_engine(
        resolved_settings.url,
        pool_pre_ping=True,
        pool_size=DEFAULT_POOL_SIZE,
        max_overflow=DEFAULT_MAX_OVERFLOW,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the given engine."""
    return sessionmaker(
        bind=engine,
        class_=Session,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
