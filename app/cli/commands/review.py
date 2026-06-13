"""Review synchronization CLI commands."""

from __future__ import annotations

import time

import typer

from app.cli.dependencies import review_sync_service
from app.cli.errors import handle_cli_error
from app.cli.output import echo_sync_summary


def register(app: typer.Typer) -> None:
    """Register review synchronization commands."""

    @app.command("sync-reviews")
    def sync_reviews(
        owner: str = typer.Argument(help="GitHub repository owner."),
        repository: str = typer.Argument(help="GitHub repository name."),
    ) -> None:
        """Synchronize pull request reviews for a registered repository."""
        repository_name = f"{owner}/{repository}"
        typer.echo(f"Syncing reviews for {repository_name}...")
        started_at = time.perf_counter()

        try:
            with review_sync_service() as service:
                result = service.sync_repository_reviews(owner, repository)
        except Exception as error:
            handle_cli_error(error)

        echo_sync_summary(
            total_processed=result.total_processed,
            created=result.created_count,
            updated=result.updated_count,
            elapsed_seconds=time.perf_counter() - started_at,
        )
