"""GitHub REST API integration."""

from app.collector.github.client import (
    GitHubClient,
    build_pagination_info,
    parse_link_header,
)
from app.collector.github.exceptions import (
    AuthenticationError,
    GitHubError,
    GitHubResponseInfo,
    PullRequestNotFound,
    RateLimitExceeded,
    RepositoryNotFound,
    UnexpectedGitHubResponse,
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

__all__ = [
    "AuthenticationError",
    "FileChange",
    "GitHubClient",
    "GitHubError",
    "GitHubResponseInfo",
    "PaginatedResponse",
    "PaginationInfo",
    "PullRequest",
    "PullRequestNotFound",
    "RateLimitExceeded",
    "RateLimitInfo",
    "Repository",
    "RepositoryNotFound",
    "UnexpectedGitHubResponse",
    "Review",
    "ReviewComment",
    "build_pagination_info",
    "parse_link_header",
]
