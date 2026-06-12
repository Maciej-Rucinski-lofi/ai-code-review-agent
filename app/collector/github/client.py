"""GitHub REST API client."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar
from urllib.parse import parse_qs, urlparse

import httpx

from app.collector.config import GitHubSettings
from app.collector.github.exceptions import (
    AuthenticationError,
    GitHubError,
    GitHubResponseInfo,
    PullRequestNotFound,
    RateLimitExceeded,
    RepositoryNotFound,
    build_response_info,
)
from app.collector.github.models import (
    FileChange,
    PaginatedResponse,
    PaginationInfo,
    PullRequest,
    RateLimitInfo,
    Repository,
    Review,
    ReviewComment,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
LinkMap = dict[str, str]
RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})
LINK_REL_PATTERN = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


@dataclass(frozen=True, slots=True)
class GitHubRequestResult:
    """Successful HTTP response from the GitHub API."""

    status_code: int
    url: str
    json_body: Any
    headers: dict[str, str]
    rate_limit: RateLimitInfo
    pagination: PaginationInfo


def parse_link_header(link_header: str | None) -> LinkMap:
    """Parse GitHub RFC 5988 Link headers into a rel-to-URL mapping."""
    if not link_header:
        return {}

    links: LinkMap = {}
    for match in LINK_REL_PATTERN.finditer(link_header):
        url, rel = match.groups()
        links[rel] = url
    return links


def _extract_page_number(url: str | None) -> int | None:
    """Extract the page query parameter from a GitHub pagination URL."""
    if url is None:
        return None

    query = parse_qs(urlparse(url).query)
    page_values = query.get("page")
    if not page_values:
        return None
    return int(page_values[0])


def build_pagination_info(
    headers: dict[str, str],
    *,
    current_page: int | None = None,
) -> PaginationInfo:
    """Build pagination metadata from GitHub response headers."""
    links = parse_link_header(headers.get("link"))
    return PaginationInfo(
        current_page=current_page,
        next_page=_extract_page_number(links.get("next")),
        previous_page=_extract_page_number(links.get("prev")),
        last_page=_extract_page_number(links.get("last")),
        first_page=_extract_page_number(links.get("first")),
        next_url=links.get("next"),
        previous_url=links.get("prev"),
        last_url=links.get("last"),
        first_url=links.get("first"),
    )


class GitHubClient:
    """HTTP client for the GitHub REST API."""

    def __init__(
        self,
        settings: GitHubSettings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Initialize the client with optional settings and HTTP client."""
        self._settings = settings or GitHubSettings.from_env()
        self._default_headers = self._build_default_headers()
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.Client(
            base_url=self._settings.base_url,
            timeout=self._settings.timeout_seconds,
        )

    def close(self) -> None:
        """Close the underlying HTTP client when owned by this instance."""
        if self._owns_client:
            self._http_client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def get_repository(self, owner: str, name: str) -> Repository:
        """Return repository metadata for the given owner and name."""
        result = self._request_json("GET", f"/repos/{owner}/{name}")
        return Repository.from_api(result.json_body)

    def get_pull_requests(
        self,
        owner: str,
        repository: str,
        state: str,
        page: int,
        *,
        per_page: int = 100,
    ) -> PaginatedResponse[PullRequest]:
        """Return one page of pull requests for a repository."""
        result = self._request_json(
            "GET",
            f"/repos/{owner}/{repository}/pulls",
            params={"state": state, "page": page, "per_page": per_page},
        )
        items = [PullRequest.from_api(item) for item in result.json_body]
        pagination = build_pagination_info(
            result.headers,
            current_page=page,
        )
        return PaginatedResponse(items=items, pagination=pagination)

    def get_single_pull_request(
        self,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> PullRequest:
        """Return a single pull request by number."""
        result = self._request_json(
            "GET",
            f"/repos/{owner}/{repository}/pulls/{pull_request_number}",
        )
        return PullRequest.from_api(result.json_body)

    def get_reviews(
        self,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> list[Review]:
        """Return reviews submitted for a pull request."""
        result = self._request_json(
            "GET",
            f"/repos/{owner}/{repository}/pulls/{pull_request_number}/reviews",
        )
        return [Review.from_api(item) for item in result.json_body]

    def get_review_comments(
        self,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> list[ReviewComment]:
        """Return inline review comments for a pull request."""
        result = self._request_json(
            "GET",
            f"/repos/{owner}/{repository}/pulls/{pull_request_number}/comments",
        )
        return [ReviewComment.from_api(item) for item in result.json_body]

    def get_pull_request_files(
        self,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> list[FileChange]:
        """Return changed files and patches for a pull request."""
        result = self._request_json(
            "GET",
            f"/repos/{owner}/{repository}/pulls/{pull_request_number}/files",
        )
        return [FileChange.from_api(item) for item in result.json_body]

    def _build_default_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pr-intelligence-platform",
        }
        if self._settings.token is not None:
            headers["Authorization"] = f"Bearer {self._settings.token}"
        return headers

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
    ) -> GitHubRequestResult:
        response = self._send_with_retries(method, path, params=params)
        normalized_headers = {
            key.lower(): value for key, value in response.headers.items()
        }
        rate_limit = RateLimitInfo.from_headers(normalized_headers)
        self._log_rate_limit(path, rate_limit)

        if response.status_code == 403 and self._is_rate_limit_response(response):
            raise self._build_rate_limit_error(response, rate_limit)

        if response.status_code in {401, 403}:
            raise self._build_authentication_error(response)

        if response.status_code == 404:
            raise self._build_not_found_error(path, response)

        if response.status_code >= 400:
            raise self._build_generic_error(response)

        logger.info(
            "GitHub API response received",
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "rate_limit_remaining": rate_limit.remaining,
            },
        )

        return GitHubRequestResult(
            status_code=response.status_code,
            url=str(response.request.url),
            json_body=response.json(),
            headers=normalized_headers,
            rate_limit=rate_limit,
            pagination=build_pagination_info(normalized_headers),
        )

    def _send_with_retries(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
    ) -> httpx.Response:
        attempts = self._settings.max_retries + 1
        last_response: httpx.Response | None = None

        for attempt in range(1, attempts + 1):
            logger.info(
                "GitHub API request started",
                extra={
                    "method": method,
                    "path": path,
                    "attempt": attempt,
                    "authenticated": self._settings.is_authenticated,
                },
            )
            response = self._http_client.request(
                method,
                path,
                params=params,
                headers=self._default_headers,
            )
            last_response = response

            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response

            if attempt >= attempts:
                return response

            delay_seconds = min(2 ** (attempt - 1), 8)
            logger.warning(
                "Retrying GitHub API request after server error",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "attempt": attempt,
                    "delay_seconds": delay_seconds,
                },
            )
            time.sleep(delay_seconds)

        if last_response is None:
            msg = "GitHub request failed before a response was received"
            raise GitHubError(msg)
        return last_response

    def _log_rate_limit(self, path: str, rate_limit: RateLimitInfo) -> None:
        if rate_limit.remaining is None:
            return

        extra = {
            "path": path,
            "rate_limit_limit": rate_limit.limit,
            "rate_limit_remaining": rate_limit.remaining,
            "rate_limit_reset_at": (
                rate_limit.reset_at.isoformat() if rate_limit.reset_at else None
            ),
        }

        if rate_limit.remaining == 0:
            logger.warning("GitHub API rate limit exhausted", extra=extra)
            return

        if rate_limit.remaining <= 10:
            logger.warning("GitHub API rate limit nearly exhausted", extra=extra)
            return

        logger.debug("GitHub API rate limit status", extra=extra)

    @staticmethod
    def _is_rate_limit_response(response: httpx.Response) -> bool:
        if response.status_code == 429:
            return True
        if response.status_code != 403:
            return False

        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            return True

        try:
            payload = response.json()
        except ValueError:
            return False

        message = str(payload.get("message", "")).lower()
        return "rate limit" in message

    @staticmethod
    def _response_info(response: httpx.Response) -> GitHubResponseInfo:
        return build_response_info(
            status_code=response.status_code,
            url=str(response.request.url),
            body=response.text,
            headers=dict(response.headers),
        )

    def _build_rate_limit_error(
        self,
        response: httpx.Response,
        rate_limit: RateLimitInfo,
    ) -> RateLimitExceeded:
        reset_at = (
            int(rate_limit.reset_at.timestamp())
            if rate_limit.reset_at is not None
            else None
        )
        return RateLimitExceeded(
            "GitHub API rate limit exceeded",
            response=self._response_info(response),
            remaining=rate_limit.remaining,
            reset_at=reset_at,
        )

    def _build_authentication_error(
        self, response: httpx.Response
    ) -> AuthenticationError:
        return AuthenticationError(
            "GitHub authentication failed",
            response=self._response_info(response),
        )

    def _build_not_found_error(
        self,
        path: str,
        response: httpx.Response,
    ) -> GitHubError:
        response_info = self._response_info(response)
        if "/pulls/" in path:
            return PullRequestNotFound(
                "Pull request not found",
                response=response_info,
            )
        if path.startswith("/repos/"):
            return RepositoryNotFound(
                "Repository not found",
                response=response_info,
            )
        return GitHubError(
            "GitHub resource not found",
            response=response_info,
        )

    @staticmethod
    def _build_generic_error(response: httpx.Response) -> GitHubError:
        return GitHubError(
            f"GitHub API request failed with status {response.status_code}",
            response=GitHubClient._response_info(response),
        )


def map_paginated_items(
    result: GitHubRequestResult,
    mapper: Callable[[dict[str, Any]], T],
    *,
    current_page: int | None = None,
) -> PaginatedResponse[T]:
    """Map a paginated GitHub JSON array response into typed DTOs."""
    if not isinstance(result.json_body, list):
        msg = "Expected a JSON array for paginated GitHub response"
        raise TypeError(msg)

    pagination = build_pagination_info(result.headers, current_page=current_page)
    return PaginatedResponse(
        items=[mapper(item) for item in result.json_body],
        pagination=pagination,
    )
