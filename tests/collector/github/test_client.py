"""Tests for the GitHub API client."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.collector.config import GitHubSettings
from app.collector.github.client import GitHubClient
from app.collector.github.exceptions import (
    AuthenticationError,
    PullRequestNotFound,
    RateLimitExceeded,
    RepositoryNotFound,
)
from app.collector.github.models import (
    FileChange,
    PullRequest,
    Repository,
    Review,
    ReviewComment,
)

REPO_PAYLOAD: dict[str, Any] = {
    "id": 123,
    "name": "django",
    "full_name": "django/django",
    "description": "The Web framework for perfectionists with deadlines.",
    "default_branch": "main",
    "html_url": "https://github.com/django/django",
    "owner": {"login": "django"},
}

PR_PAYLOAD: dict[str, Any] = {
    "id": 456,
    "number": 42,
    "title": "Fix queryset caching",
    "body": "Fixes an edge case.",
    "state": "closed",
    "html_url": "https://github.com/django/django/pull/42",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-02T10:00:00Z",
    "merged_at": "2024-01-02T09:00:00Z",
    "user": {"login": "alice"},
}

REVIEW_PAYLOAD: dict[str, Any] = {
    "id": 789,
    "state": "APPROVED",
    "body": "Looks good.",
    "submitted_at": "2024-01-02T08:00:00Z",
    "html_url": "https://github.com/django/django/pull/42#review-789",
    "user": {"login": "bob"},
}

REVIEW_COMMENT_PAYLOAD: dict[str, Any] = {
    "id": 1011,
    "body": "Consider renaming this variable.",
    "path": "django/db/models/query.py",
    "line": 12,
    "original_line": 10,
    "diff_hunk": "@@ -10,3 +10,4 @@",
    "created_at": "2024-01-02T07:30:00Z",
    "pull_request_review_id": 789,
    "html_url": "https://github.com/django/django/pull/42#discussion_r1011",
    "user": {"login": "bob"},
}

FILE_CHANGE_PAYLOAD: dict[str, Any] = {
    "filename": "django/db/models/query.py",
    "status": "modified",
    "additions": 3,
    "deletions": 1,
    "changes": 4,
    "patch": "@@ -1 +1 @@",
    "previous_filename": None,
}


def _json_response(
    payload: Any,
    *,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    response_headers = {
        "Content-Type": "application/json",
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Remaining": "4999",
        "X-RateLimit-Reset": "1700000000",
    }
    if headers:
        response_headers.update(headers)

    request = httpx.Request("GET", "https://api.github.com/test")
    return httpx.Response(
        status_code=status_code,
        headers=response_headers,
        content=json.dumps(payload).encode(),
        request=request,
    )


def _build_client(
    handler: httpx.MockTransport,
    *,
    token: str | None = "ghp_test_token",
) -> GitHubClient:
    settings = GitHubSettings(
        token=token,
        base_url="https://api.github.com",
        timeout_seconds=5.0,
        max_retries=2,
    )
    http_client = httpx.Client(
        transport=handler,
        base_url=settings.base_url,
        headers={"Accept": "application/vnd.github+json"},
    )
    return GitHubClient(settings=settings, http_client=http_client)


def test_authenticated_requests_include_bearer_token() -> None:
    """Authenticated clients should send a bearer token header."""
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return _json_response(REPO_PAYLOAD)

    client = _build_client(httpx.MockTransport(handler))
    repository = client.get_repository("django", "django")

    assert repository.name == "django"
    assert captured_headers["authorization"] == "Bearer ghp_test_token"


def test_anonymous_requests_do_not_include_authorization() -> None:
    """Anonymous clients should omit authorization headers."""
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return _json_response(REPO_PAYLOAD)

    client = _build_client(httpx.MockTransport(handler), token=None)
    client.get_repository("django", "django")

    assert "authorization" not in captured_headers


def test_get_repository_returns_repository_dto() -> None:
    """Repository retrieval should map API payloads into DTOs."""
    client = _build_client(
        httpx.MockTransport(lambda _request: _json_response(REPO_PAYLOAD)),
    )

    repository = client.get_repository("django", "django")

    assert isinstance(repository, Repository)
    assert repository.github_id == 123
    assert repository.owner == "django"
    assert repository.default_branch == "main"


def test_get_pull_requests_returns_paginated_response() -> None:
    """Pull request listing should include pagination metadata."""
    link_header = (
        '<https://api.github.com/repos/django/django/pulls?page=3>; rel="next", '
        '<https://api.github.com/repos/django/django/pulls?page=10>; rel="last"'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["state"] == "closed"
        assert request.url.params["page"] == "2"
        return _json_response([PR_PAYLOAD], headers={"Link": link_header})

    client = _build_client(httpx.MockTransport(handler))
    response = client.get_pull_requests("django", "django", "closed", page=2)

    assert len(response.items) == 1
    assert isinstance(response.items[0], PullRequest)
    assert response.items[0].number == 42
    assert response.pagination.current_page == 2
    assert response.pagination.next_page == 3
    assert response.pagination.last_page == 10
    assert response.pagination.has_next is True


def test_get_single_pull_request_returns_pull_request_dto() -> None:
    """Single pull request retrieval should map API payloads into DTOs."""
    client = _build_client(
        httpx.MockTransport(lambda _request: _json_response(PR_PAYLOAD)),
    )

    pull_request = client.get_single_pull_request("django", "django", 42)

    assert pull_request.number == 42
    assert pull_request.author_login == "alice"
    assert pull_request.merged_at == datetime(2024, 1, 2, 9, 0, tzinfo=UTC)


def test_get_reviews_returns_review_dtos() -> None:
    """Review retrieval should map API payloads into DTOs."""
    client = _build_client(
        httpx.MockTransport(lambda _request: _json_response([REVIEW_PAYLOAD])),
    )

    reviews = client.get_reviews("django", "django", 42)

    assert len(reviews) == 1
    assert isinstance(reviews[0], Review)
    assert reviews[0].reviewer_login == "bob"
    assert reviews[0].state == "APPROVED"


def test_get_review_comments_returns_comment_dtos() -> None:
    """Review comment retrieval should map API payloads into DTOs."""
    client = _build_client(
        httpx.MockTransport(
            lambda _request: _json_response([REVIEW_COMMENT_PAYLOAD]),
        ),
    )

    comments = client.get_review_comments("django", "django", 42)

    assert len(comments) == 1
    assert isinstance(comments[0], ReviewComment)
    assert comments[0].file_path == "django/db/models/query.py"
    assert comments[0].line_number == 12


def test_get_pull_request_files_returns_file_change_dtos() -> None:
    """File retrieval should map API payloads into DTOs."""
    client = _build_client(
        httpx.MockTransport(
            lambda _request: _json_response([FILE_CHANGE_PAYLOAD]),
        ),
    )

    files = client.get_pull_request_files("django", "django", 42)

    assert len(files) == 1
    assert isinstance(files[0], FileChange)
    assert files[0].filename == "django/db/models/query.py"
    assert files[0].patch == "@@ -1 +1 @@"


def test_repository_not_found_raises_dedicated_exception() -> None:
    """Missing repositories should raise RepositoryNotFound."""
    client = _build_client(
        httpx.MockTransport(lambda _request: _json_response({}, status_code=404)),
    )

    with pytest.raises(RepositoryNotFound) as exc_info:
        client.get_repository("missing", "repo")

    assert exc_info.value.status_code == 404
    assert exc_info.value.response is not None


def test_pull_request_not_found_raises_dedicated_exception() -> None:
    """Missing pull requests should raise PullRequestNotFound."""
    client = _build_client(
        httpx.MockTransport(lambda _request: _json_response({}, status_code=404)),
    )

    with pytest.raises(PullRequestNotFound):
        client.get_single_pull_request("django", "django", 999)


def test_authentication_error_for_invalid_credentials() -> None:
    """Invalid credentials should raise AuthenticationError."""
    client = _build_client(
        httpx.MockTransport(lambda _request: _json_response({}, status_code=401)),
    )

    with pytest.raises(AuthenticationError):
        client.get_repository("django", "django")


def test_rate_limit_exceeded_raises_dedicated_exception() -> None:
    """Rate limit responses should raise RateLimitExceeded."""
    payload = {"message": "API rate limit exceeded for user."}

    def handler(_request: httpx.Request) -> httpx.Response:
        return _json_response(
            payload,
            status_code=403,
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1700000100",
            },
        )

    client = _build_client(httpx.MockTransport(handler))

    with pytest.raises(RateLimitExceeded) as exc_info:
        client.get_repository("django", "django")

    assert exc_info.value.remaining == 0
    assert exc_info.value.reset_at == 1700000100


def test_retries_transient_server_errors() -> None:
    """Transient server errors should be retried before failing."""
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return _json_response({}, status_code=503)
        return _json_response(REPO_PAYLOAD)

    settings = GitHubSettings(
        token="ghp_test_token",
        base_url="https://api.github.com",
        timeout_seconds=5.0,
        max_retries=2,
    )
    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url=settings.base_url,
    )
    client = GitHubClient(settings=settings, http_client=http_client)

    repository = client.get_repository("django", "django")

    assert repository.github_id == 123
    assert attempts["count"] == 2
