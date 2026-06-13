"""Pull request synchronization CLI commands."""

from __future__ import annotations

import time
from typing import Annotated

import typer

from app.cli.dependencies import pull_request_sync_service
from app.cli.errors import handle_cli_error
from app.cli.output import echo_sync_summary


def register(app: typer.Typer) -> None:
    """Register pull request synchronization commands."""

    @app.command("sync-prs")
    def sync_prs(
        owner: str = typer.Argument(help="GitHub repository owner."),
        repository: str = typer.Argument(help="GitHub repository name."),
        max_pages: Annotated[
            int | None,
            typer.Option("--max-pages", min=1, help="Maximum pages to fetch."),
        ] = None,
    ) -> None:
        """Synchronize pull requests for a registered repository."""
        repository_name = f"{owner}/{repository}"
        typer.echo(f"Syncing pull requests for {repository_name}...")
        started_at = time.perf_counter()

        try:
            with pull_request_sync_service() as service:
                result = service.sync_repository_pull_requests(
                    owner,
                    repository,
                    max_pages=max_pages,
                )
        except Exception as error:
            handle_cli_error(error)

        echo_sync_summary(
            total_processed=result.total_processed,
            created=result.created_count,
            updated=result.updated_count,
            elapsed_seconds=time.perf_counter() - started_at,
        )
