# Goal

Create the initial database model layer for the PR Intelligence Platform.

The implementation must follow:

* docs/domain-model.md
* docs/architecture.md
* docs/tech-stack.md
* .cursor/project_context.mdc
* .cursor/engineering_standards.mdc
* .cursor/architecture_principles.mdc

Read all referenced documents before generating code.

---

# Context

The project collects historical GitHub Pull Requests, review comments and AI-generated analysis results.

This task only creates database models.

No GitHub integration should be implemented.

No business logic should be implemented.

No API endpoints should be implemented.

No AI functionality should be implemented.

---

# Requirements

Use:

* SQLAlchemy 2.x
* Declarative mappings
* Type annotations
* PostgreSQL-compatible types

Create the following entities:

## Repository

Fields:

* id
* github_id
* owner
* name
* description
* default_branch
* created_at
* updated_at

---

## PullRequest

Fields:

* id
* github_id
* repository_id
* number
* title
* body
* state
* author_login
* created_at
* updated_at
* merged_at

Relationships:

* belongs to Repository

---

## FileChange

Fields:

* id
* pull_request_id
* filename
* additions
* deletions
* changes
* patch

Relationships:

* belongs to PullRequest

---

## Review

Fields:

* id
* github_id
* pull_request_id
* reviewer_login
* state
* submitted_at

Relationships:

* belongs to PullRequest

---

## ReviewComment

Fields:

* id
* github_id
* review_id
* pull_request_id
* body
* file_path
* line_number
* created_at

Relationships:

* belongs to Review
* belongs to PullRequest

---

## Analysis

Fields:

* id
* pull_request_id
* model_name
* finding
* severity
* confidence_score
* created_at

Relationships:

* belongs to PullRequest

---

## BenchmarkResult

Fields:

* id
* analysis_id
* precision
* recall
* match_rate
* created_at

Relationships:

* belongs to Analysis

---

# Technical Requirements

Create:

app/database/models/

Structure:

app/
└── database/
└── models/
├── base.py
├── repository.py
├── pull_request.py
├── file_change.py
├── review.py
├── review_comment.py
├── analysis.py
├── benchmark_result.py
└── **init**.py

Requirements:

* one model per file
* no circular imports
* explicit relationships
* proper foreign keys
* indexes for GitHub identifiers
* indexes for frequently queried fields

---

# Out of Scope

Do NOT implement:

* Alembic migrations
* repositories pattern
* service layer
* GitHub client
* API routes
* OpenAI integration
* benchmark logic

Those will be implemented in later tasks.

---

# Acceptance Criteria

* SQLAlchemy models compile successfully
* all relationships are valid
* type checking passes
* Ruff passes
* no unused code
* no placeholder implementations

Before generating code:

1. Explain the proposed model structure.
2. Explain relationships.
3. Identify any potential improvements.
4. Wait for approval if architectural concerns exist.

Generate production-quality code only.
