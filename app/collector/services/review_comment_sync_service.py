"""Review comment synchronization between GitHub and PostgreSQL."""

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
    ReviewNotFound,
    UnexpectedGitHubResponse,
)
from app.collector.github.models import ReviewComment as GitHubReviewComment
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.repositories.review_comment_repository import ReviewCommentRepository
from app.collector.repositories.review_repository import ReviewRepository
from app.collector.schemas.review_comment_sync_result import ReviewCommentSyncResult
from app.database.models.pull_request import PullRequest
from app.database.models.review import Review
from app.database.models.review_comment import ReviewComment

logger = logging.getLogger(__name__)


class ReviewCommentSyncService:
    """Synchronize GitHub pull request review comments into PostgreSQL."""

    def __init__(
        self,
        github_client: GitHubClient,
        repository_repository: RepositoryRepository,
        pull_request_repository: PullRequestRepository,
        review_repository: ReviewRepository,
        review_comment_repository: ReviewCommentRepository,
    ) -> None:
        """Initialize the service with GitHub and persistence dependencies."""
        self._github_client = github_client
        self._repository_repository = repository_repository
        self._pull_request_repository = pull_request_repository
        self._review_repository = review_repository
        self._review_comment_repository = review_comment_repository

    def sync_pull_request_comments(
        self,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> ReviewCommentSyncResult:
        """Synchronize all review comments for a specific pull request."""
        local_repository = self._repository_repository.find_by_owner_and_name(
            owner,
            repository,
        )
        if local_repository is None:
            logger.error(
                "Review comment synchronization failed because repository "
                "is not registered",
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
                "Review comment synchronization failed because pull request "
                "is not registered",
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

        return self._sync_comments_for_pull_request(
            owner=owner,
            repository=repository,
            local_pull_request=local_pull_request,
            pull_request_number=pull_request_number,
        )

    def sync_repository_comments(
        self,
        owner: str,
        repository: str,
        *,
        limit: int | None = None,
    ) -> ReviewCommentSyncResult:
        """Synchronize review comments for pull requests stored for a repository."""
        local_repository = self._repository_repository.find_by_owner_and_name(
            owner,
            repository,
        )
        if local_repository is None:
            logger.error(
                "Review comment synchronization failed because repository "
                "is not registered",
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
            "Repository review comment synchronization started",
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
            result = self._sync_comments_for_pull_request(
                owner=owner,
                repository=repository,
                local_pull_request=local_pull_request,
                pull_request_number=local_pull_request.number,
            )
            total_processed += result.total_processed
            created_count += result.created_count
            updated_count += result.updated_count

        synchronized_at = datetime.now(UTC)
        aggregate_result = ReviewCommentSyncResult(
            pull_request_id=None,
            total_processed=total_processed,
            created_count=created_count,
            updated_count=updated_count,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "Repository review comment synchronization completed",
            extra={
                "owner": owner,
                "repository": repository,
                "total_processed": aggregate_result.total_processed,
                "created_count": aggregate_result.created_count,
                "updated_count": aggregate_result.updated_count,
            },
        )
        return aggregate_result

    def _sync_comments_for_pull_request(
        self,
        *,
        owner: str,
        repository: str,
        local_pull_request: PullRequest,
        pull_request_number: int,
    ) -> ReviewCommentSyncResult:
        """Fetch and synchronize review comments for one registered pull request."""
        logger.info(
            "Review comment synchronization started",
            extra={
                "owner": owner,
                "repository": repository,
                "pull_request_id": local_pull_request.id,
                "pull_request_number": pull_request_number,
            },
        )

        github_comments = self._fetch_comments(
            owner=owner,
            repository=repository,
            pull_request_number=pull_request_number,
        )

        logger.info(
            "Review comments fetched from GitHub",
            extra={
                "owner": owner,
                "repository": repository,
                "pull_request_number": pull_request_number,
                "comment_count": len(github_comments),
            },
        )

        created_count, updated_count = self._synchronize_comments(
            pull_request_id=local_pull_request.id,
            github_comments=github_comments,
        )

        synchronized_at = datetime.now(UTC)
        result = ReviewCommentSyncResult(
            pull_request_id=local_pull_request.id,
            total_processed=len(github_comments),
            created_count=created_count,
            updated_count=updated_count,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "Review comment synchronization completed",
            extra={
                "pull_request_id": result.pull_request_id,
                "total_processed": result.total_processed,
                "created_count": result.created_count,
                "updated_count": result.updated_count,
            },
        )
        return result

    def _fetch_comments(
        self,
        *,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> list[GitHubReviewComment]:
        """Fetch review comments from GitHub and map client errors."""
        try:
            return self._github_client.get_review_comments(
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
                "Review comment synchronization failed while fetching from GitHub",
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
                "Review comment synchronization failed due to unexpected "
                "GitHub response",
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

    def _synchronize_comments(
        self,
        *,
        pull_request_id: int,
        github_comments: list[GitHubReviewComment],
    ) -> tuple[int, int]:
        """Create or update review comments for a fetched pull request."""
        if not github_comments:
            return 0, 0

        review_github_ids = self._collect_review_github_ids(github_comments)
        reviews_by_github_id = self._review_repository.find_by_github_ids(
            review_github_ids,
        )

        github_ids = [comment.github_id for comment in github_comments]
        existing_by_github_id = self._review_comment_repository.find_by_github_ids(
            github_ids,
        )

        created_count = 0
        updated_count = 0

        for github_comment in github_comments:
            local_review = self._resolve_review(
                github_comment=github_comment,
                reviews_by_github_id=reviews_by_github_id,
            )
            existing = existing_by_github_id.get(github_comment.github_id)
            if existing is None:
                self._create_comment(
                    pull_request_id=pull_request_id,
                    review_id=local_review.id,
                    github_comment=github_comment,
                )
                created_count += 1
                logger.info(
                    "Review comment created",
                    extra={
                        "pull_request_id": pull_request_id,
                        "github_id": github_comment.github_id,
                        "review_id": local_review.id,
                        "file_path": github_comment.file_path,
                    },
                )
                continue

            self._update_comment(
                existing=existing,
                pull_request_id=pull_request_id,
                review_id=local_review.id,
                github_comment=github_comment,
            )
            updated_count += 1
            logger.info(
                "Review comment updated",
                extra={
                    "pull_request_id": pull_request_id,
                    "github_id": github_comment.github_id,
                    "review_id": local_review.id,
                    "file_path": github_comment.file_path,
                },
            )

        return created_count, updated_count

    def _collect_review_github_ids(
        self,
        github_comments: list[GitHubReviewComment],
    ) -> list[int]:
        """Return unique GitHub review identifiers referenced by comments."""
        review_github_ids: list[int] = []
        seen: set[int] = set()
        for github_comment in github_comments:
            review_github_id = github_comment.pull_request_review_id
            if review_github_id is None or review_github_id in seen:
                continue
            seen.add(review_github_id)
            review_github_ids.append(review_github_id)
        return review_github_ids

    def _resolve_review(
        self,
        *,
        github_comment: GitHubReviewComment,
        reviews_by_github_id: dict[int, Review],
    ) -> Review:
        """Map a GitHub comment to its locally synchronized review."""
        review_github_id = github_comment.pull_request_review_id
        if review_github_id is None:
            logger.error(
                "Review comment synchronization failed because comment has no review",
                extra={"github_id": github_comment.github_id},
            )
            raise ReviewNotFound(
                f"Review comment {github_comment.github_id} is not linked to a review.",
            )

        local_review = reviews_by_github_id.get(review_github_id)
        if local_review is None:
            logger.error(
                "Review comment synchronization failed because review is not registered",
                extra={
                    "github_id": github_comment.github_id,
                    "review_github_id": review_github_id,
                },
            )
            raise ReviewNotFound(
                f"Review {review_github_id} for comment "
                f"{github_comment.github_id} is not registered.",
            )

        return local_review

    def _create_comment(
        self,
        *,
        pull_request_id: int,
        review_id: int,
        github_comment: GitHubReviewComment,
    ) -> ReviewComment:
        """Persist a new review comment from GitHub metadata."""
        return self._review_comment_repository.create(
            github_id=github_comment.github_id,
            review_id=review_id,
            pull_request_id=pull_request_id,
            body=github_comment.body,
            file_path=github_comment.file_path,
            line_number=github_comment.line_number,
            created_at=github_comment.created_at,
        )

    def _update_comment(
        self,
        *,
        existing: ReviewComment,
        pull_request_id: int,
        review_id: int,
        github_comment: GitHubReviewComment,
    ) -> ReviewComment:
        """Refresh an existing review comment with the latest GitHub metadata."""
        return self._review_comment_repository.update(
            existing,
            github_id=github_comment.github_id,
            review_id=review_id,
            pull_request_id=pull_request_id,
            body=github_comment.body,
            file_path=github_comment.file_path,
            line_number=github_comment.line_number,
            created_at=github_comment.created_at,
        )
