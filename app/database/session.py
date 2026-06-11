"""Database session management helpers."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker

from app.database.config import DatabaseSettings
from app.database.engine import create_db_engine, create_session_factory

_engine = create_db_engine()
_session_factory = create_session_factory(_engine)


def get_session_factory(
    settings: DatabaseSettings | None = None,
) -> sessionmaker[Session]:
    """Return a session factory, optionally using custom settings."""
    if settings is None:
        return _session_factory

    engine = create_db_engine(settings)
    return create_session_factory(engine)


def get_session(settings: DatabaseSettings | None = None) -> Session:
    """Create a new database session."""
    return get_session_factory(settings)()


@contextmanager
def session_scope(settings: DatabaseSettings | None = None) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = get_session(settings)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session(
    settings: DatabaseSettings | None = None,
) -> Generator[Session, None, None]:
    """Yield a database session for dependency injection (e.g. FastAPI)."""
    session = get_session(settings)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
