"""File change synchronization between GitHub and PostgreSQL."""

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
from app.collector.github.models import FileChange as GitHubFileChange
from app.collector.repositories.file_change_repository import FileChangeRepository
from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.schemas.file_change_sync_result import FileChangeSyncResult
from app.database.models.file_change import FileChange
from app.database.models.pull_request import PullRequest

logger = logging.getLogger(__name__)


class FileChangeSyncService:
    """Synchronize GitHub pull request file changes into PostgreSQL."""

    def __init__(
        self,
        github_client: GitHubClient,
        repository_repository: RepositoryRepository,
        pull_request_repository: PullRequestRepository,
        file_change_repository: FileChangeRepository,
    ) -> None:
        """Initialize the service with GitHub and persistence dependencies."""
        self._github_client = github_client
        self._repository_repository = repository_repository
        self._pull_request_repository = pull_request_repository
        self._file_change_repository = file_change_repository

    def sync_pull_request_files(
        self,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> FileChangeSyncResult:
        """Synchronize all file changes for a specific pull request."""
        local_repository = self._repository_repository.find_by_owner_and_name(
            owner,
            repository,
        )
        if local_repository is None:
            logger.error(
                "File change synchronization failed because repository "
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
                "File change synchronization failed because pull request "
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

        return self._sync_files_for_pull_request(
            owner=owner,
            repository=repository,
            local_pull_request=local_pull_request,
            pull_request_number=pull_request_number,
        )

    def sync_repository_files(
        self,
        owner: str,
        repository: str,
        *,
        limit: int | None = None,
    ) -> FileChangeSyncResult:
        """Synchronize file changes for pull requests stored for a repository."""
        local_repository = self._repository_repository.find_by_owner_and_name(
            owner,
            repository,
        )
        if local_repository is None:
            logger.error(
                "File change synchronization failed because repository "
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
            "Repository file change synchronization started",
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
            result = self._sync_files_for_pull_request(
                owner=owner,
                repository=repository,
                local_pull_request=local_pull_request,
                pull_request_number=local_pull_request.number,
            )
            total_processed += result.total_processed
            created_count += result.created_count
            updated_count += result.updated_count

        synchronized_at = datetime.now(UTC)
        aggregate_result = FileChangeSyncResult(
            pull_request_id=None,
            total_processed=total_processed,
            created_count=created_count,
            updated_count=updated_count,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "Repository file change synchronization completed",
            extra={
                "owner": owner,
                "repository": repository,
                "total_processed": aggregate_result.total_processed,
                "created_count": aggregate_result.created_count,
                "updated_count": aggregate_result.updated_count,
            },
        )
        return aggregate_result

    def _sync_files_for_pull_request(
        self,
        *,
        owner: str,
        repository: str,
        local_pull_request: PullRequest,
        pull_request_number: int,
    ) -> FileChangeSyncResult:
        """Fetch and synchronize file changes for one registered pull request."""
        logger.info(
            "File change synchronization started",
            extra={
                "owner": owner,
                "repository": repository,
                "pull_request_id": local_pull_request.id,
                "pull_request_number": pull_request_number,
            },
        )

        github_files = self._fetch_files(
            owner=owner,
            repository=repository,
            pull_request_number=pull_request_number,
        )

        logger.info(
            "File changes fetched from GitHub",
            extra={
                "owner": owner,
                "repository": repository,
                "pull_request_number": pull_request_number,
                "file_count": len(github_files),
            },
        )

        created_count, updated_count = self._synchronize_files(
            pull_request_id=local_pull_request.id,
            github_files=github_files,
        )

        synchronized_at = datetime.now(UTC)
        result = FileChangeSyncResult(
            pull_request_id=local_pull_request.id,
            total_processed=len(github_files),
            created_count=created_count,
            updated_count=updated_count,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "File change synchronization completed",
            extra={
                "pull_request_id": result.pull_request_id,
                "total_processed": result.total_processed,
                "created_count": result.created_count,
                "updated_count": result.updated_count,
            },
        )
        return result

    def _fetch_files(
        self,
        *,
        owner: str,
        repository: str,
        pull_request_number: int,
    ) -> list[GitHubFileChange]:
        """Fetch file changes from GitHub and map client errors."""
        try:
            return self._github_client.get_pull_request_files(
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
                "File change synchronization failed while fetching from GitHub",
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
                "File change synchronization failed due to unexpected "
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

    def _synchronize_files(
        self,
        *,
        pull_request_id: int,
        github_files: list[GitHubFileChange],
    ) -> tuple[int, int]:
        """Create or update file changes for a fetched pull request."""
        if not github_files:
            self._remove_stale_files(
                pull_request_id=pull_request_id,
                current_filenames=set(),
            )
            return 0, 0

        filenames = [github_file.filename for github_file in github_files]
        existing_by_filename = (
            self._file_change_repository.find_by_pull_request_and_filenames(
                pull_request_id,
                filenames,
            )
        )

        created_count = 0
        updated_count = 0
        current_filenames: set[str] = set()

        for github_file in github_files:
            current_filenames.add(github_file.filename)
            existing = existing_by_filename.get(github_file.filename)
            if existing is None:
                self._create_file_change(
                    pull_request_id=pull_request_id,
                    github_file=github_file,
                )
                created_count += 1
                logger.info(
                    "File change created",
                    extra={
                        "pull_request_id": pull_request_id,
                        "filename": github_file.filename,
                        "additions": github_file.additions,
                        "deletions": github_file.deletions,
                        "changes": github_file.changes,
                    },
                )
                continue

            self._update_file_change(
                existing=existing,
                pull_request_id=pull_request_id,
                github_file=github_file,
            )
            updated_count += 1
            logger.info(
                "File change updated",
                extra={
                    "pull_request_id": pull_request_id,
                    "filename": github_file.filename,
                    "additions": github_file.additions,
                    "deletions": github_file.deletions,
                    "changes": github_file.changes,
                },
            )

        self._remove_stale_files(
            pull_request_id=pull_request_id,
            current_filenames=current_filenames,
        )
        return created_count, updated_count

    def _remove_stale_files(
        self,
        *,
        pull_request_id: int,
        current_filenames: set[str],
    ) -> None:
        """Remove local file changes no longer present in the GitHub response."""
        local_files = self._file_change_repository.find_by_pull_request_id(
            pull_request_id,
        )
        stale_ids = [
            local_file.id
            for local_file in local_files
            if local_file.filename not in current_filenames
        ]
        if not stale_ids:
            return

        self._file_change_repository.delete_by_ids(stale_ids)
        logger.info(
            "Stale file changes removed",
            extra={
                "pull_request_id": pull_request_id,
                "removed_count": len(stale_ids),
            },
        )

    def _create_file_change(
        self,
        *,
        pull_request_id: int,
        github_file: GitHubFileChange,
    ) -> FileChange:
        """Persist a new file change from GitHub metadata."""
        return self._file_change_repository.create(
            pull_request_id=pull_request_id,
            filename=github_file.filename,
            additions=github_file.additions,
            deletions=github_file.deletions,
            changes=github_file.changes,
            patch=github_file.patch,
        )

    def _update_file_change(
        self,
        *,
        existing: FileChange,
        pull_request_id: int,
        github_file: GitHubFileChange,
    ) -> FileChange:
        """Refresh an existing file change with the latest GitHub metadata."""
        return self._file_change_repository.update(
            existing,
            pull_request_id=pull_request_id,
            filename=github_file.filename,
            additions=github_file.additions,
            deletions=github_file.deletions,
            changes=github_file.changes,
            patch=github_file.patch,
        )
