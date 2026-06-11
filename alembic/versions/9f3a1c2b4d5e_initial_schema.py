"""Initial schema for PR Intelligence Platform models.

Revision ID: 9f3a1c2b4d5e
Revises:
Create Date: 2026-06-11 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f3a1c2b4d5e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all application tables."""
    op.create_table(
        "repositories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_repositories_github_id"),
        "repositories",
        ["github_id"],
        unique=True,
    )
    op.create_index(op.f("ix_repositories_name"), "repositories", ["name"], unique=False)
    op.create_index(
        op.f("ix_repositories_owner"),
        "repositories",
        ["owner"],
        unique=False,
    )

    op.create_table(
        "pull_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("author_login", sa.String(length=255), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "number"),
    )
    op.create_index(
        op.f("ix_pull_requests_author_login"),
        "pull_requests",
        ["author_login"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pull_requests_github_id"),
        "pull_requests",
        ["github_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_pull_requests_merged_at"),
        "pull_requests",
        ["merged_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pull_requests_number"),
        "pull_requests",
        ["number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pull_requests_repository_id"),
        "pull_requests",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pull_requests_state"),
        "pull_requests",
        ["state"],
        unique=False,
    )

    op.create_table(
        "file_changes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("pull_request_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=1024), nullable=False),
        sa.Column("additions", sa.Integer(), nullable=False),
        sa.Column("deletions", sa.Integer(), nullable=False),
        sa.Column("changes", sa.Integer(), nullable=False),
        sa.Column("patch", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_file_changes_filename"),
        "file_changes",
        ["filename"],
        unique=False,
    )
    op.create_index(
        op.f("ix_file_changes_pull_request_id"),
        "file_changes",
        ["pull_request_id"],
        unique=False,
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("pull_request_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewer_login", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_reviews_github_id"),
        "reviews",
        ["github_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_reviews_pull_request_id"),
        "reviews",
        ["pull_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reviews_reviewer_login"),
        "reviews",
        ["reviewer_login"],
        unique=False,
    )
    op.create_index(op.f("ix_reviews_state"), "reviews", ["state"], unique=False)
    op.create_index(
        op.f("ix_reviews_submitted_at"),
        "reviews",
        ["submitted_at"],
        unique=False,
    )

    op.create_table(
        "review_comments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("review_id", sa.BigInteger(), nullable=False),
        sa.Column("pull_request_id", sa.BigInteger(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"]),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_comments_created_at"),
        "review_comments",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_comments_file_path"),
        "review_comments",
        ["file_path"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_comments_github_id"),
        "review_comments",
        ["github_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_review_comments_pull_request_id"),
        "review_comments",
        ["pull_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_comments_review_id"),
        "review_comments",
        ["review_id"],
        unique=False,
    )

    op.create_table(
        "analyses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("pull_request_id", sa.BigInteger(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("finding", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analyses_created_at"),
        "analyses",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analyses_model_name"),
        "analyses",
        ["model_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analyses_pull_request_id"),
        "analyses",
        ["pull_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analyses_severity"),
        "analyses",
        ["severity"],
        unique=False,
    )

    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("analysis_id", sa.BigInteger(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("match_rate", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_benchmark_results_analysis_id"),
        "benchmark_results",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_benchmark_results_created_at"),
        "benchmark_results",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all application tables."""
    op.drop_index(
        op.f("ix_benchmark_results_created_at"),
        table_name="benchmark_results",
    )
    op.drop_index(
        op.f("ix_benchmark_results_analysis_id"),
        table_name="benchmark_results",
    )
    op.drop_table("benchmark_results")

    op.drop_index(op.f("ix_analyses_severity"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_pull_request_id"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_model_name"), table_name="analyses")
    op.drop_index(op.f("ix_analyses_created_at"), table_name="analyses")
    op.drop_table("analyses")

    op.drop_index(op.f("ix_review_comments_review_id"), table_name="review_comments")
    op.drop_index(
        op.f("ix_review_comments_pull_request_id"),
        table_name="review_comments",
    )
    op.drop_index(op.f("ix_review_comments_github_id"), table_name="review_comments")
    op.drop_index(op.f("ix_review_comments_file_path"), table_name="review_comments")
    op.drop_index(op.f("ix_review_comments_created_at"), table_name="review_comments")
    op.drop_table("review_comments")

    op.drop_index(op.f("ix_reviews_submitted_at"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_state"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_reviewer_login"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_pull_request_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_github_id"), table_name="reviews")
    op.drop_table("reviews")

    op.drop_index(op.f("ix_file_changes_pull_request_id"), table_name="file_changes")
    op.drop_index(op.f("ix_file_changes_filename"), table_name="file_changes")
    op.drop_table("file_changes")

    op.drop_index(op.f("ix_pull_requests_state"), table_name="pull_requests")
    op.drop_index(op.f("ix_pull_requests_repository_id"), table_name="pull_requests")
    op.drop_index(op.f("ix_pull_requests_number"), table_name="pull_requests")
    op.drop_index(op.f("ix_pull_requests_merged_at"), table_name="pull_requests")
    op.drop_index(op.f("ix_pull_requests_github_id"), table_name="pull_requests")
    op.drop_index(op.f("ix_pull_requests_author_login"), table_name="pull_requests")
    op.drop_table("pull_requests")

    op.drop_index(op.f("ix_repositories_owner"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_name"), table_name="repositories")
    op.drop_index(op.f("ix_repositories_github_id"), table_name="repositories")
    op.drop_table("repositories")
