"""CLI output formatting helpers."""

from __future__ import annotations

import typer


def format_duration(seconds: float) -> str:
    """Format elapsed seconds for display."""
    return f"{seconds:.2f}s"


def echo_sync_summary(
    *,
    total_processed: int,
    created: int,
    updated: int,
    elapsed_seconds: float,
) -> None:
    """Display a standardized synchronization summary."""
    typer.echo(f"Total processed: {total_processed}")
    typer.echo(f"Created: {created}")
    typer.echo(f"Updated: {updated}")
    typer.echo(f"Execution time: {format_duration(elapsed_seconds)}")
