"""Review synchronization between GitHub and PostgreSQL."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.collector.github.client import GitHubClient
from app.collector.github.exceptions import (
    AuthenticationError,
    GitHubError,
    PullRequestNotFound,
    RateLimitExceeded,
    RepositoryNotFound,
    UnexpectedGitHubResponse,
)
from app.collector.github.models import Review as GitHubReview
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.repositories.review_repository import ReviewRepository
from app.collector.schemas.review_sync_result import ReviewSyncResult
from app.database.models.pull_request import PullRequest
from app.database.models.review import Review

logger = logging.getLogger(__name__)

PENDING_REVIEW_SUBMITTED_AT_FALLBACK = datetime(1970, 1, 1, tzinfo=UTC)


class ReviewSyncService:
    """Synchronize GitHub pull request reviews into PostgreSQL."""

    def __init__(
        self,
        github_client: GitHubClient,
        repository_repository: RepositoryRepository,
        pull_request_repository: PullRequestRepository,
        review_repository: ReviewRepository,
    ) -> None:
        """Initialize the service with GitHub and persistence dependencies."""
        self._github_client = github_client
        self._repository_repository = repository_repository
        self._pull_request_repository = pull_request_repository
        self._review_repository = review_repository

    def sync_pull_request_reviews(
        self,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> ReviewSyncResult:
        """Synchronize all reviews for a specific pull request."""
        local_repository = self._repository_repository.find_by_owner_and_name(
            owner,
            repository,
        )
        if local_repository is None:
            logger.error(
                "Review synchronization failed because repository is not registered",
                extra={"owner": owner, "repository": repository},
            )
            raise RepositoryNotFound(
                f"Repository {owner}/{repository} is not registered.",
            )

        local_pull_request = self._pull_request_repository.find_by_repository_and_number(
            local_repository.id,
            pull_request_number,
        )
        if local_pull_request is None:
            logger.error(
                "Review synchronization failed because pull request is not registered",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "pull_request_number": pull_request_number,
                },
            )
            raise PullRequestNotFound(
                f"Pull request {owner}/{repository}#{pull_request_number} "
                "is not registered.",
            )

        return self._sync_reviews_for_pull_request(
            owner=owner,
            repository=repository,
            local_pull_request=local_pull_request,
            pull_request_number=pull_request_number,
        )

    def sync_repository_reviews(
        self,
        owner: str,
        repository: str,
        *,
        limit: int | None = None,
    ) -> ReviewSyncResult:
        """Synchronize reviews for pull requests stored for a repository."""
        local_repository = self._repository_repository.find_by_owner_and_name(
            owner,
            repository,
        )
        if local_repository is None:
            logger.error(
                "Review synchronization failed because repository is not registered",
                extra={"owner": owner, "repository": repository},
            )
            raise RepositoryNotFound(
                f"Repository {owner}/{repository} is not registered.",
            )

        local_pull_requests = self._pull_request_repository.find_by_repository_id(
            local_repository.id,
            limit=limit,
        )

        logger.info(
            "Repository review synchronization started",
            extra={
                "owner": owner,
                "repository": repository,
                "pull_request_count": len(local_pull_requests),
                "limit": limit,
            },
        )

        total_processed = 0
        created_count = 0
        updated_count = 0

        for local_pull_request in local_pull_requests:
            result = self._sync_reviews_for_pull_request(
                owner=owner,
                repository=repository,
                local_pull_request=local_pull_request,
                pull_request_number=local_pull_request.number,
            )
            total_processed += result.total_processed
            created_count += result.created_count
            updated_count += result.updated_count

        synchronized_at = datetime.now(UTC)
        aggregate_result = ReviewSyncResult(
            pull_request_id=None,
            total_processed=total_processed,
            created_count=created_count,
            updated_count=updated_count,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "Repository review synchronization completed",
            extra={
                "owner": owner,
                "repository": repository,
                "total_processed": aggregate_result.total_processed,
                "created_count": aggregate_result.created_count,
                "updated_count": aggregate_result.updated_count,
            },
        )
        return aggregate_result

    def _sync_reviews_for_pull_request(
        self,
        *,
        owner: str,
        repository: str,
        local_pull_request: PullRequest,
        pull_request_number: int,
    ) -> ReviewSyncResult:
        """Fetch and synchronize reviews for one registered pull request."""
        logger.info(
            "Review synchronization started",
            extra={
                "owner": owner,
                "repository": repository,
                "pull_request_id": local_pull_request.id,
                "pull_request_number": pull_request_number,
            },
        )

        github_reviews = self._fetch_reviews(
            owner=owner,
            repository=repository,
            pull_request_number=pull_request_number,
        )

        logger.info(
            "Reviews fetched from GitHub",
            extra={
                "owner": owner,
                "repository": repository,
                "pull_request_number": pull_request_number,
                "review_count": len(github_reviews),
            },
        )

        created_count, updated_count = self._synchronize_reviews(
            pull_request_id=local_pull_request.id,
            github_reviews=github_reviews,
        )

        synchronized_at = datetime.now(UTC)
        result = ReviewSyncResult(
            pull_request_id=local_pull_request.id,
            total_processed=len(github_reviews),
            created_count=created_count,
            updated_count=updated_count,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "Review synchronization completed",
            extra={
                "pull_request_id": result.pull_request_id,
                "total_processed": result.total_processed,
                "created_count": result.created_count,
                "updated_count": result.updated_count,
            },
        )
        return result

    def _fetch_reviews(
        self,
        *,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> list[GitHubReview]:
        """Fetch reviews from GitHub and map client errors."""
        try:
            return self._github_client.get_reviews(
                owner,
                repository,
                pull_request_number,
            )
        except (
            PullRequestNotFound,
            RepositoryNotFound,
            AuthenticationError,
            RateLimitExceeded,
            UnexpectedGitHubResponse,
        ) as error:
            logger.error(
                "Review synchronization failed while fetching from GitHub",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "pull_request_number": pull_request_number,
                    "error_type": type(error).__name__,
                    "status_code": error.status_code,
                },
            )
            raise
        except GitHubError as error:
            logger.error(
                "Review synchronization failed due to unexpected GitHub response",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "pull_request_number": pull_request_number,
                    "error_type": type(error).__name__,
                    "status_code": error.status_code,
                },
            )
            raise UnexpectedGitHubResponse(
                error.message,
                response=error.response,
            ) from error

    def _synchronize_reviews(
        self,
        *,
        pull_request_id: int,
        github_reviews: list[GitHubReview],
    ) -> tuple[int, int]:
        """Create or update reviews for a fetched pull request."""
        if not github_reviews:
            return 0, 0

        github_ids = [review.github_id for review in github_reviews]
        existing_by_github_id = self._review_repository.find_by_github_ids(github_ids)

        created_count = 0
        updated_count = 0

        for github_review in github_reviews:
            existing = existing_by_github_id.get(github_review.github_id)
            if existing is None:
                self._create_review(
                    pull_request_id=pull_request_id,
                    github_review=github_review,
                )
                created_count += 1
                logger.info(
                    "Review created",
                    extra={
                        "pull_request_id": pull_request_id,
                        "github_id": github_review.github_id,
                        "state": github_review.state,
                    },
                )
                continue

            self._update_review(
                existing=existing,
                pull_request_id=pull_request_id,
                github_review=github_review,
            )
            updated_count += 1
            logger.info(
                "Review updated",
                extra={
                    "pull_request_id": pull_request_id,
                    "github_id": github_review.github_id,
                    "state": github_review.state,
                },
            )

        return created_count, updated_count

    def _create_review(
        self,
        *,
        pull_request_id: int,
        github_review: GitHubReview,
    ) -> Review:
        """Persist a new review from GitHub metadata."""
        return self._review_repository.create(
            github_id=github_review.github_id,
            pull_request_id=pull_request_id,
            reviewer_login=github_review.reviewer_login,
            state=github_review.state,
            submitted_at=self._resolve_submitted_at(github_review),
        )

    def _update_review(
        self,
        *,
        existing: Review,
        pull_request_id: int,
        github_review: GitHubReview,
    ) -> Review:
        """Refresh an existing review with the latest GitHub metadata."""
        return self._review_repository.update(
            existing,
            github_id=github_review.github_id,
            pull_request_id=pull_request_id,
            reviewer_login=github_review.reviewer_login,
            state=github_review.state,
            submitted_at=self._resolve_submitted_at(github_review),
        )

    @staticmethod
    def _resolve_submitted_at(github_review: GitHubReview) -> datetime:
        """Return submitted_at from GitHub or a fallback for pending reviews."""
        if github_review.submitted_at is not None:
            return github_review.submitted_at
        return PENDING_REVIEW_SUBMITTED_AT_FALLBACK
