"""Collector persistence layer."""

from app.collector.repositories.pull_request_repository import PullRequestRepository
from app.collector.repositories.repository_repository import RepositoryRepository

__all__ = ["PullRequestRepository", "RepositoryRepository"]
