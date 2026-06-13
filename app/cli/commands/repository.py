"""Repository synchronization CLI commands."""

from __future__ import annotations

import time

import typer

from app.cli.dependencies import repository_sync_service
from app.cli.errors import handle_cli_error
from app.cli.output import format_duration


def register(app: typer.Typer) -> None:
    """Register repository synchronization commands."""

    @app.command("sync-repository")
    def sync_repository(
        owner: str = typer.Argument(help="GitHub repository owner."),
        repository: str = typer.Argument(help="GitHub repository name."),
    ) -> None:
        """Synchronize repository metadata from GitHub into the database."""
        repository_name = f"{owner}/{repository}"
        typer.echo(f"Syncing repository {repository_name}...")
        started_at = time.perf_counter()

        try:
            with repository_sync_service() as service:
                result = service.sync_repository(owner, repository)
        except Exception as error:
            handle_cli_error(error)

        elapsed_seconds = time.perf_counter() - started_at
        typer.echo(f"Repository: {repository_name}")
        typer.echo(f"Action: {result.action}")
        typer.echo(f"Execution time: {format_duration(elapsed_seconds)}")
