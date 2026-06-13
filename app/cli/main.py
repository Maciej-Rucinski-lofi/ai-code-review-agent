"""CLI entry point for PR Intelligence Platform operations."""

from __future__ import annotations

import typer

from app.cli.commands import (
    file_change,
    pull_request,
    repository,
    review,
    review_comment,
    stats,
)

app = typer.Typer(
    name="pr-intelligence",
    help="Execute synchronization workflows and operational tasks.",
    add_completion=False,
    no_args_is_help=True,
)

repository.register(app)
pull_request.register(app)
review.register(app)
review_comment.register(app)
file_change.register(app)
stats.register(app)


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
