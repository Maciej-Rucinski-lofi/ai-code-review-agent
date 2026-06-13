"""Collection statistics CLI commands."""

from __future__ import annotations

import typer

from app.cli.dependencies import fetch_collection_stats
from app.cli.errors import handle_cli_error


def register(app: typer.Typer) -> None:
    """Register read-only statistics commands."""

    @app.command("stats")
    def stats() -> None:
        """Display read-only collection statistics from the database."""
        try:
            collection_stats = fetch_collection_stats()
        except Exception as error:
            handle_cli_error(error)

        typer.echo(f"Repositories: {collection_stats.repositories}")
        typer.echo(f"Pull Requests: {collection_stats.pull_requests}")
        typer.echo(f"Reviews: {collection_stats.reviews}")
        typer.echo(f"Review Comments: {collection_stats.review_comments}")
        typer.echo(f"File Changes: {collection_stats.file_changes}")
