"""GitHub API client exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubResponseInfo:
    """Snapshot of an HTTP response for error reporting."""

    status_code: int
    url: str
    body: str
    headers: dict[str, str]


class GitHubError(Exception):
    """Base exception for GitHub API client failures."""

    def __init__(
        self,
        message: str,
        *,
        response: GitHubResponseInfo | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.response = response

    @property
    def status_code(self) -> int | None:
        """HTTP status code from the failed response, if available."""
        if self.response is None:
            return None
        return self.response.status_code


class RateLimitExceeded(GitHubError):
    """Raised when the GitHub API rate limit has been exceeded."""

    def __init__(
        self,
        message: str,
        *,
        response: GitHubResponseInfo | None = None,
        remaining: int | None = None,
        reset_at: int | None = None,
    ) -> None:
        super().__init__(message, response=response)
        self.remaining = remaining
        self.reset_at = reset_at


class AuthenticationError(GitHubError):
    """Raised when GitHub rejects the configured credentials."""


class RepositoryNotFound(GitHubError):
    """Raised when a repository cannot be found."""


class PullRequestNotFound(GitHubError):
    """Raised when a pull request cannot be found."""


class ReviewNotFound(GitHubError):
    """Raised when a review cannot be found."""


class UnexpectedGitHubResponse(GitHubError):
    """Raised when the GitHub API returns an unexpected or malformed response."""


def build_response_info(
    *,
    status_code: int,
    url: str,
    body: str,
    headers: dict[str, Any],
) -> GitHubResponseInfo:
    """Build a typed response snapshot from raw HTTP data."""
    normalized_headers = {
        str(key).lower(): str(value) for key, value in headers.items()
    }
    return GitHubResponseInfo(
        status_code=status_code,
        url=url,
        body=body,
        headers=normalized_headers,
    )
