"""Pull request synchronization between GitHub and PostgreSQL."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.collector.github.client import GitHubClient
from app.collector.github.exceptions import (
    AuthenticationError,
    GitHubError,
    RateLimitExceeded,
    RepositoryNotFound,
    UnexpectedGitHubResponse,
)
from app.collector.github.models import PaginatedResponse
from app.collector.github.models import PullRequest as GitHubPullRequest
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.schemas.pull_request_sync_result import PullRequestSyncResult
from app.database.models.pull_request import PullRequest

logger = logging.getLogger(__name__)

DEFAULT_PER_PAGE = 100
DEFAULT_RECENT_MAX_PAGES = 1


class PullRequestSyncService:
    """Synchronize GitHub pull request metadata into PostgreSQL."""

    def __init__(
        self,
        github_client: GitHubClient,
        repository_repository: RepositoryRepository,
        pull_request_repository: PullRequestRepository,
    ) -> None:
        """Initialize the service with GitHub and persistence dependencies."""
        self._github_client = github_client
        self._repository_repository = repository_repository
        self._pull_request_repository = pull_request_repository

    def sync_recent_pull_requests(
        self,
        owner: str,
        repository: str,
        *,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int = DEFAULT_RECENT_MAX_PAGES,
        state: str = "all",
    ) -> PullRequestSyncResult:
        """Synchronize the latest pull requests for a registered repository."""
        return self._sync_pull_requests(
            owner=owner,
            repository=repository,
            per_page=per_page,
            max_pages=max_pages,
            state=state,
        )

    def sync_repository_pull_requests(
        self,
        owner: str,
        repository: str,
        *,
        per_page: int = DEFAULT_PER_PAGE,
        max_pages: int | None = None,
        state: str = "all",
    ) -> PullRequestSyncResult:
        """Synchronize pull request history for a registered repository."""
        return self._sync_pull_requests(
            owner=owner,
            repository=repository,
            per_page=per_page,
            max_pages=max_pages,
            state=state,
        )

    def _sync_pull_requests(
        self,
        *,
        owner: str,
        repository: str,
        per_page: int,
        max_pages: int | None,
        state: str,
    ) -> PullRequestSyncResult:
        """Fetch and synchronize pull requests with pagination support."""
        logger.info(
            "Pull request synchronization started",
            extra={
                "owner": owner,
                "repository": repository,
                "per_page": per_page,
                "max_pages": max_pages,
                "state": state,
            },
        )

        local_repository = self._repository_repository.find_by_owner_and_name(
            owner,
            repository,
        )
        if local_repository is None:
            logger.error(
                "Pull request synchronization failed because repository is not registered",
                extra={"owner": owner, "repository": repository},
            )
            raise RepositoryNotFound(
                f"Repository {owner}/{repository} is not registered.",
            )

        created_count = 0
        updated_count = 0
        total_processed = 0
        page = 1

        while True:
            response = self._fetch_pull_requests_page(
                owner=owner,
                repository=repository,
                state=state,
                page=page,
                per_page=per_page,
            )
            page_created, page_updated = self._synchronize_page(
                repository_id=local_repository.id,
                github_pull_requests=response.items,
            )
            created_count += page_created
            updated_count += page_updated
            total_processed += len(response.items)

            logger.info(
                "Pull request page processed",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "page": page,
                    "page_size": len(response.items),
                    "created_count": page_created,
                    "updated_count": page_updated,
                },
            )

            if not response.pagination.has_next:
                break
            if max_pages is not None and page >= max_pages:
                break
            page += 1

        synchronized_at = datetime.now(UTC)
        result = PullRequestSyncResult(
            repository_id=local_repository.id,
            total_processed=total_processed,
            created_count=created_count,
            updated_count=updated_count,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "Pull request synchronization completed",
            extra={
                "repository_id": result.repository_id,
                "total_processed": result.total_processed,
                "created_count": result.created_count,
                "updated_count": result.updated_count,
            },
        )
        return result

    def _fetch_pull_requests_page(
        self,
        *,
        owner: str,
        repository: str,
        state: str,
        page: int,
        per_page: int,
    ) -> PaginatedResponse[GitHubPullRequest]:
        """Fetch one page of pull requests from GitHub and map client errors."""
        try:
            return self._github_client.get_pull_requests(
                owner,
                repository,
                state,
                page=page,
                per_page=per_page,
            )
        except (
            RepositoryNotFound,
            AuthenticationError,
            RateLimitExceeded,
            UnexpectedGitHubResponse,
        ) as error:
            logger.error(
                "Pull request synchronization failed while fetching from GitHub",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "page": page,
                    "error_type": type(error).__name__,
                    "status_code": error.status_code,
                },
            )
            raise
        except GitHubError as error:
            logger.error(
                "Pull request synchronization failed due to unexpected GitHub response",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "page": page,
                    "error_type": type(error).__name__,
                    "status_code": error.status_code,
                },
            )
            raise UnexpectedGitHubResponse(
                error.message,
                response=error.response,
            ) from error

    def _synchronize_page(
        self,
        *,
        repository_id: int,
        github_pull_requests: list[GitHubPullRequest],
    ) -> tuple[int, int]:
        """Create or update pull requests for a single fetched page."""
        if not github_pull_requests:
            return 0, 0

        github_ids = [pull_request.github_id for pull_request in github_pull_requests]
        existing_by_github_id = self._pull_request_repository.find_by_github_ids(
            github_ids,
        )

        created_count = 0
        updated_count = 0

        for github_pull_request in github_pull_requests:
            existing = existing_by_github_id.get(github_pull_request.github_id)
            if existing is None:
                self._create_pull_request(
                    repository_id=repository_id,
                    github_pull_request=github_pull_request,
                )
                created_count += 1
                logger.info(
                    "Pull request created",
                    extra={
                        "repository_id": repository_id,
                        "github_id": github_pull_request.github_id,
                        "number": github_pull_request.number,
                    },
                )
                continue

            self._update_pull_request(
                existing=existing,
                repository_id=repository_id,
                github_pull_request=github_pull_request,
            )
            updated_count += 1
            logger.info(
                "Pull request updated",
                extra={
                    "repository_id": repository_id,
                    "github_id": github_pull_request.github_id,
                    "number": github_pull_request.number,
                },
            )

        return created_count, updated_count

    def _create_pull_request(
        self,
        *,
        repository_id: int,
        github_pull_request: GitHubPullRequest,
    ) -> PullRequest:
        """Persist a new pull request from GitHub metadata."""
        return self._pull_request_repository.create(
            github_id=github_pull_request.github_id,
            repository_id=repository_id,
            number=github_pull_request.number,
            title=github_pull_request.title,
            body=github_pull_request.body,
            state=github_pull_request.state,
            author_login=github_pull_request.author_login,
            created_at=github_pull_request.created_at,
            updated_at=github_pull_request.updated_at,
            merged_at=github_pull_request.merged_at,
        )

    def _update_pull_request(
        self,
        *,
        existing: PullRequest,
        repository_id: int,
        github_pull_request: GitHubPullRequest,
    ) -> PullRequest:
        """Refresh an existing pull request with the latest GitHub metadata."""
        return self._pull_request_repository.update(
            existing,
            github_id=github_pull_request.github_id,
            repository_id=repository_id,
            number=github_pull_request.number,
            title=github_pull_request.title,
            body=github_pull_request.body,
            state=github_pull_request.state,
            author_login=github_pull_request.author_login,
            created_at=github_pull_request.created_at,
            updated_at=github_pull_request.updated_at,
            merged_at=github_pull_request.merged_at,
        )
