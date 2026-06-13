"""File change synchronization CLI commands."""

from __future__ import annotations

import time

import typer

from app.cli.dependencies import file_change_sync_service
from app.cli.errors import handle_cli_error
from app.cli.output import echo_sync_summary


def register(app: typer.Typer) -> None:
    """Register file change synchronization commands."""

    @app.command("sync-files")
    def sync_files(
        owner: str = typer.Argument(help="GitHub repository owner."),
        repository: str = typer.Argument(help="GitHub repository name."),
    ) -> None:
        """Synchronize pull request file changes for a registered repository."""
        repository_name = f"{owner}/{repository}"
        typer.echo(f"Syncing file changes for {repository_name}...")
        started_at = time.perf_counter()

        try:
            with file_change_sync_service() as service:
                result = service.sync_repository_files(owner, repository)
        except Exception as error:
            handle_cli_error(error)

        echo_sync_summary(
            total_processed=result.total_processed,
            created=result.created_count,
            updated=result.updated_count,
            elapsed_seconds=time.perf_counter() - started_at,
        )
