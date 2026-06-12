"""Repository synchronization between GitHub and PostgreSQL."""

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
from app.collector.github.models import Repository as GitHubRepository
from app.collector.repositories.repository_repository import RepositoryRepository
from app.collector.schemas.repository_sync_result import (
    RepositorySyncAction,
    RepositorySyncResult,
)
from app.database.models.repository import Repository

logger = logging.getLogger(__name__)


class RepositorySyncService:
    """Synchronize GitHub repository metadata into PostgreSQL."""

    def __init__(
        self,
        github_client: GitHubClient,
        repository_repository: RepositoryRepository,
    ) -> None:
        """Initialize the service with GitHub and persistence dependencies."""
        self._github_client = github_client
        self._repository_repository = repository_repository

    def sync_repository(self, owner: str, repository: str) -> RepositorySyncResult:
        """Fetch repository metadata from GitHub and create or update the local record."""
        logger.info(
            "Repository synchronization started",
            extra={"owner": owner, "repository": repository},
        )

        github_repository = self._fetch_github_repository(owner, repository)

        logger.info(
            "Repository fetched from GitHub",
            extra={
                "owner": owner,
                "repository": repository,
                "github_id": github_repository.github_id,
            },
        )

        existing = self._find_existing_repository(
            github_repository=github_repository,
            owner=owner,
            name=repository,
        )
        synchronized_at = datetime.now(UTC)

        if existing is None:
            persisted = self._create_repository(github_repository)
            action = RepositorySyncAction.CREATED
            logger.info(
                "Repository created",
                extra={
                    "repository_id": persisted.id,
                    "github_id": persisted.github_id,
                    "owner": persisted.owner,
                    "name": persisted.name,
                },
            )
        else:
            persisted = self._update_repository(existing, github_repository)
            action = RepositorySyncAction.UPDATED
            logger.info(
                "Repository updated",
                extra={
                    "repository_id": persisted.id,
                    "github_id": persisted.github_id,
                    "owner": persisted.owner,
                    "name": persisted.name,
                },
            )

        result = RepositorySyncResult(
            repository_id=persisted.id,
            github_id=persisted.github_id,
            action=action,
            synchronized_at=synchronized_at,
        )

        logger.info(
            "Repository synchronization completed",
            extra={
                "repository_id": result.repository_id,
                "github_id": result.github_id,
                "action": result.action,
            },
        )
        return result

    def _fetch_github_repository(self, owner: str, repository: str) -> GitHubRepository:
        """Fetch repository metadata from GitHub and map client errors."""
        try:
            return self._github_client.get_repository(owner, repository)
        except (
            RepositoryNotFound,
            AuthenticationError,
            RateLimitExceeded,
            UnexpectedGitHubResponse,
        ) as error:
            logger.error(
                "Repository synchronization failed while fetching from GitHub",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "error_type": type(error).__name__,
                    "status_code": error.status_code,
                },
            )
            raise
        except GitHubError as error:
            logger.error(
                "Repository synchronization failed due to unexpected GitHub response",
                extra={
                    "owner": owner,
                    "repository": repository,
                    "error_type": type(error).__name__,
                    "status_code": error.status_code,
                },
            )
            raise UnexpectedGitHubResponse(
                error.message,
                response=error.response,
            ) from error

    def _find_existing_repository(
        self,
        *,
        github_repository: GitHubRepository,
        owner: str,
        name: str,
    ) -> Repository | None:
        """Locate an existing record by GitHub ID, then by owner and name."""
        existing = self._repository_repository.find_by_github_id(
            github_repository.github_id,
        )
        if existing is not None:
            return existing
        return self._repository_repository.find_by_owner_and_name(owner, name)

    def _create_repository(self, github_repository: GitHubRepository) -> Repository:
        """Persist a new repository from GitHub metadata."""
        return self._repository_repository.create(
            github_id=github_repository.github_id,
            owner=github_repository.owner,
            name=github_repository.name,
            description=github_repository.description,
            default_branch=github_repository.default_branch,
        )

    def _update_repository(
        self,
        existing: Repository,
        github_repository: GitHubRepository,
    ) -> Repository:
        """Refresh an existing repository with the latest GitHub metadata."""
        return self._repository_repository.update(
            existing,
            github_id=github_repository.github_id,
            owner=github_repository.owner,
            name=github_repository.name,
            description=github_repository.description,
            default_branch=github_repository.default_branch,
        )
