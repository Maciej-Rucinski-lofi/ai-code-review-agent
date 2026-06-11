"""Tests for collector GitHub configuration."""

from __future__ import annotations

import pytest

from app.collector.config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    GITHUB_API_BASE_URL,
    GitHubSettings,
)


@pytest.fixture
def github_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set predictable GitHub environment variables for tests."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.setenv("GITHUB_API_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("GITHUB_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("GITHUB_MAX_RETRIES", "5")


def test_github_settings_load_from_environment(github_env: None) -> None:
    """GitHub settings should reflect configured environment variables."""
    settings = GitHubSettings.from_env()

    assert settings.token == "ghp_test_token"
    assert settings.base_url == "https://api.example.com"
    assert settings.timeout_seconds == 15.0
    assert settings.max_retries == 5
    assert settings.is_authenticated is True


def test_github_settings_allow_anonymous_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing or blank tokens should produce unauthenticated settings."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    settings = GitHubSettings.from_env()

    assert settings.token is None
    assert settings.is_authenticated is False
    assert settings.base_url == GITHUB_API_BASE_URL
    assert settings.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert settings.max_retries == DEFAULT_MAX_RETRIES


def test_github_settings_treat_blank_token_as_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace-only tokens should be treated as absent."""
    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    settings = GitHubSettings.from_env()

    assert settings.token is None
    assert settings.is_authenticated is False
