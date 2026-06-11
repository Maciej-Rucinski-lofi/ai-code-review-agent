"""Collector configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 3
GITHUB_API_BASE_URL = "https://api.github.com"


@dataclass(frozen=True, slots=True)
class GitHubSettings:
    """GitHub API connection settings."""

    token: str | None
    base_url: str
    timeout_seconds: float
    max_retries: int

    @classmethod
    def from_env(cls) -> GitHubSettings:
        """Load GitHub settings from environment variables."""
        token = os.environ.get("GITHUB_TOKEN")
        if token is not None and token.strip() == "":
            token = None

        timeout_raw = os.environ.get(
            "GITHUB_TIMEOUT_SECONDS",
            str(DEFAULT_TIMEOUT_SECONDS),
        )
        retries_raw = os.environ.get("GITHUB_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))

        return cls(
            token=token,
            base_url=os.environ.get("GITHUB_API_BASE_URL", GITHUB_API_BASE_URL),
            timeout_seconds=float(timeout_raw),
            max_retries=int(retries_raw),
        )

    @property
    def is_authenticated(self) -> bool:
        """Return whether a GitHub token is configured."""
        return self.token is not None
