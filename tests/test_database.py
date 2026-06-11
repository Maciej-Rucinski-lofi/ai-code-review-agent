"""Tests for database configuration, engine, and session management."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.database.config import DatabaseSettings
from app.database.engine import create_db_engine, create_session_factory
from app.database.session import get_session, get_session_factory


@pytest.fixture
def database_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Set predictable database environment variables for tests."""
    monkeypatch.setenv("DATABASE_HOST", "db.example.com")
    monkeypatch.setenv("DATABASE_PORT", "5433")
    monkeypatch.setenv("DATABASE_NAME", "test_db")
    monkeypatch.setenv("DATABASE_USER", "test_user")
    monkeypatch.setenv("DATABASE_PASSWORD", "test_password")
    yield


def test_database_settings_load_from_environment(database_env: None) -> None:
    """Database settings should reflect configured environment variables."""
    settings = DatabaseSettings.from_env()

    assert settings.host == "db.example.com"
    assert settings.port == 5433
    assert settings.name == "test_db"
    assert settings.user == "test_user"
    assert settings.password == "test_password"


def test_database_settings_use_local_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing environment variables should fall back to local defaults."""
    for key in (
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = DatabaseSettings.from_env()

    assert settings.host == "localhost"
    assert settings.port == 5432
    assert settings.name == "pr_intelligence"
    assert settings.user == "postgres"
    assert settings.password == "postgres"


def test_database_url_is_postgresql_with_psycopg(database_env: None) -> None:
    """Generated URLs should target PostgreSQL via the psycopg driver."""
    settings = DatabaseSettings.from_env()

    assert settings.url.startswith("postgresql+psycopg://")
    assert "test_user:test_password@db.example.com:5433/test_db" in settings.url


def test_engine_creation_succeeds(database_env: None) -> None:
    """Engine creation should succeed without requiring a live connection."""
    settings = DatabaseSettings.from_env()

    engine = create_db_engine(settings)

    assert isinstance(engine, Engine)
    assert engine.url.drivername == "postgresql+psycopg"


def test_session_factory_creates_sessions(database_env: None) -> None:
    """Session factory should create SQLAlchemy session instances."""
    settings = DatabaseSettings.from_env()
    engine = create_db_engine(settings)
    session_factory = create_session_factory(engine)

    session = session_factory()

    assert isinstance(session, Session)
    session.close()


def test_get_session_factory_without_custom_settings() -> None:
    """Default session factory should create sessions."""
    session = get_session()

    assert isinstance(session, Session)
    session.close()


def test_get_session_factory_with_custom_settings(database_env: None) -> None:
    """Custom settings should produce an isolated session factory."""
    settings = DatabaseSettings.from_env()
    session_factory = get_session_factory(settings)

    session = session_factory()

    assert isinstance(session, Session)
    session.close()
