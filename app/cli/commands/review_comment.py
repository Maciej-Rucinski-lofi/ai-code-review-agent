"""Review comment synchronization CLI commands."""

from __future__ import annotations

import time

import typer

from app.cli.dependencies import review_comment_sync_service
from app.cli.errors import handle_cli_error
from app.cli.output import echo_sync_summary


def register(app: typer.Typer) -> None:
    """Register review comment synchronization commands."""

    @app.command("sync-comments")
    def sync_comments(
        owner: str = typer.Argument(help="GitHub repository owner."),
        repository: str = typer.Argument(help="GitHub repository name."),
    ) -> None:
        """Synchronize review comments for a registered repository."""
        repository_name = f"{owner}/{repository}"
        typer.echo(f"Syncing review comments for {repository_name}...")
        started_at = time.perf_counter()

        try:
            with review_comment_sync_service() as service:
                result = service.sync_repository_comments(owner, repository)
        except Exception as error:
            handle_cli_error(error)

        echo_sync_summary(
            total_processed=result.total_processed,
            created=result.created_count,
            updated=result.updated_count,
            elapsed_seconds=time.perf_counter() - started_at,
        )
