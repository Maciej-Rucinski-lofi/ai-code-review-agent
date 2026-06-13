"""CLI error handling and exit code mapping."""

from __future__ import annotations

from typing import NoReturn

import typer
from sqlalchemy.exc import SQLAlchemyError

from app.collector.github.exceptions import (
    AuthenticationError,
    GitHubError,
    PullRequestNotFound,
    RateLimitExceeded,
    RepositoryNotFound,
    ReviewNotFound,
    UnexpectedGitHubResponse,
)

EXIT_GENERAL_ERROR = 1
EXIT_AUTH_ERROR = 2
EXIT_NOT_FOUND = 3
EXIT_RATE_LIMIT = 4
EXIT_DATABASE_ERROR = 5


def handle_cli_error(error: Exception) -> NoReturn:
    """Map exceptions to user-friendly messages and non-zero exit codes."""
    if isinstance(error, RepositoryNotFound):
        typer.secho(
            f"Repository not found: {error.message}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(EXIT_NOT_FOUND) from error

    if isinstance(error, PullRequestNotFound):
        typer.secho(
            f"Pull request not found: {error.message}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(EXIT_NOT_FOUND) from error

    if isinstance(error, ReviewNotFound):
        typer.secho(
            f"Review not found: {error.message}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(EXIT_NOT_FOUND) from error

    if isinstance(error, AuthenticationError):
        typer.secho(
            "GitHub authentication failed. Check your GITHUB_TOKEN.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(EXIT_AUTH_ERROR) from error

    if isinstance(error, RateLimitExceeded):
        typer.secho(
            "GitHub rate limit exceeded. Try again later.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(EXIT_RATE_LIMIT) from error

    if isinstance(error, (UnexpectedGitHubResponse, GitHubError)):
        typer.secho(
            f"GitHub API error: {error.message}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(EXIT_GENERAL_ERROR) from error

    if isinstance(error, SQLAlchemyError):
        typer.secho(
            "Database connection failed. Check your database configuration.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(EXIT_DATABASE_ERROR) from error

    typer.secho(
        "An unexpected error occurred.",
        fg=typer.colors.RED,
        err=True,
    )
    raise typer.Exit(EXIT_GENERAL_ERROR) from error
