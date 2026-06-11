"""Data transfer objects for GitHub REST API responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse GitHub ISO-8601 timestamps into timezone-aware datetimes."""
    if value is None:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


@dataclass(frozen=True, slots=True)
class PaginationInfo:
    """Pagination metadata parsed from GitHub Link response headers."""

    current_page: int | None
    next_page: int | None
    previous_page: int | None
    last_page: int | None
    first_page: int | None
    next_url: str | None
    previous_url: str | None
    last_url: str | None
    first_url: str | None

    @property
    def has_next(self) -> bool:
        """Return whether another results page exists."""
        return self.next_page is not None or self.next_url is not None

    @property
    def has_previous(self) -> bool:
        """Return whether a previous results page exists."""
        return self.previous_page is not None or self.previous_url is not None


@dataclass(frozen=True, slots=True)
class PaginatedResponse(Generic[T]):
    """Single page of GitHub API results with pagination metadata."""

    items: list[T]
    pagination: PaginationInfo


@dataclass(frozen=True, slots=True)
class RateLimitInfo:
    """GitHub rate limit state from response headers."""

    limit: int | None
    remaining: int | None
    reset_at: datetime | None
    used: int | None

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> RateLimitInfo:
        """Parse rate limit headers from a GitHub API response."""
        reset_raw = headers.get("x-ratelimit-reset")
        reset_at = None
        if reset_raw is not None:
            reset_at = datetime.fromtimestamp(int(reset_raw), tz=UTC)

        return cls(
            limit=_parse_optional_int(headers.get("x-ratelimit-limit")),
            remaining=_parse_optional_int(headers.get("x-ratelimit-remaining")),
            reset_at=reset_at,
            used=_parse_optional_int(headers.get("x-ratelimit-used")),
        )


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value)


@dataclass(frozen=True, slots=True)
class Repository:
    """GitHub repository metadata."""

    github_id: int
    owner: str
    name: str
    full_name: str
    description: str | None
    default_branch: str
    html_url: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Repository:
        """Build a repository DTO from a GitHub API payload."""
        owner_payload = payload["owner"]
        return cls(
            github_id=int(payload["id"]),
            owner=str(owner_payload["login"]),
            name=str(payload["name"]),
            full_name=str(payload["full_name"]),
            description=payload.get("description"),
            default_branch=str(payload["default_branch"]),
            html_url=str(payload["html_url"]),
        )


@dataclass(frozen=True, slots=True)
class PullRequest:
    """GitHub pull request metadata."""

    github_id: int
    number: int
    title: str
    body: str | None
    state: str
    author_login: str
    merged_at: datetime | None
    created_at: datetime
    updated_at: datetime
    html_url: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> PullRequest:
        """Build a pull request DTO from a GitHub API payload."""
        user_payload = payload["user"]
        created_at = _parse_datetime(str(payload["created_at"]))
        updated_at = _parse_datetime(str(payload["updated_at"]))
        if created_at is None or updated_at is None:
            msg = "Pull request payload is missing created_at or updated_at"
            raise ValueError(msg)

        return cls(
            github_id=int(payload["id"]),
            number=int(payload["number"]),
            title=str(payload["title"]),
            body=payload.get("body"),
            state=str(payload["state"]),
            author_login=str(user_payload["login"]),
            merged_at=_parse_datetime(payload.get("merged_at")),
            created_at=created_at,
            updated_at=updated_at,
            html_url=str(payload["html_url"]),
        )


@dataclass(frozen=True, slots=True)
class Review:
    """GitHub pull request review."""

    github_id: int
    reviewer_login: str
    state: str
    body: str | None
    submitted_at: datetime | None
    html_url: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Review:
        """Build a review DTO from a GitHub API payload."""
        user_payload = payload["user"]
        return cls(
            github_id=int(payload["id"]),
            reviewer_login=str(user_payload["login"]),
            state=str(payload["state"]),
            body=payload.get("body"),
            submitted_at=_parse_datetime(payload.get("submitted_at")),
            html_url=str(payload["html_url"]),
        )


@dataclass(frozen=True, slots=True)
class ReviewComment:
    """Inline review comment on a pull request diff."""

    github_id: int
    author_login: str
    body: str
    file_path: str
    line_number: int | None
    original_line_number: int | None
    diff_hunk: str | None
    created_at: datetime
    pull_request_review_id: int | None
    html_url: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> ReviewComment:
        """Build a review comment DTO from a GitHub API payload."""
        user_payload = payload["user"]
        created_at = _parse_datetime(str(payload["created_at"]))
        if created_at is None:
            msg = "Review comment payload is missing created_at"
            raise ValueError(msg)

        return cls(
            github_id=int(payload["id"]),
            author_login=str(user_payload["login"]),
            body=str(payload["body"]),
            file_path=str(payload["path"]),
            line_number=payload.get("line"),
            original_line_number=payload.get("original_line"),
            diff_hunk=payload.get("diff_hunk"),
            created_at=created_at,
            pull_request_review_id=payload.get("pull_request_review_id"),
            html_url=str(payload["html_url"]),
        )


@dataclass(frozen=True, slots=True)
class FileChange:
    """Single file changed in a pull request."""

    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None
    previous_filename: str | None

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> FileChange:
        """Build a file change DTO from a GitHub API payload."""
        return cls(
            filename=str(payload["filename"]),
            status=str(payload["status"]),
            additions=int(payload["additions"]),
            deletions=int(payload["deletions"]),
            changes=int(payload["changes"]),
            patch=payload.get("patch"),
            previous_filename=payload.get("previous_filename"),
        )
