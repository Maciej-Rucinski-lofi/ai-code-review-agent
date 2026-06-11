"""Database configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.engine import URL

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5432
DEFAULT_NAME = "pr_intelligence"
DEFAULT_USER = "postgres"
DEFAULT_PASSWORD = "postgres"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """PostgreSQL connection settings."""

    host: str
    port: int
    name: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> DatabaseSettings:
        """Load database settings from environment variables."""
        port_raw = os.environ.get("DATABASE_PORT", str(DEFAULT_PORT))
        return cls(
            host=os.environ.get("DATABASE_HOST", DEFAULT_HOST),
            port=int(port_raw),
            name=os.environ.get("DATABASE_NAME", DEFAULT_NAME),
            user=os.environ.get("DATABASE_USER", DEFAULT_USER),
            password=os.environ.get("DATABASE_PASSWORD", DEFAULT_PASSWORD),
        )

    @property
    def url(self) -> str:
        """Build a SQLAlchemy-compatible PostgreSQL connection URL."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
        ).render_as_string(hide_password=False)
