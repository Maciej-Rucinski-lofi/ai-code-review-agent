# Goal

Implement Pull Request Review Comment synchronization between GitHub and PostgreSQL.

The implementation must follow:

* docs/architecture.md
* docs/domain-model.md
* docs/github-data-model.md
* docs/tech-stack.md
* .cursor/project_context.mdc
* .cursor/engineering_standards.mdc
* .cursor/architecture_principles.mdc

Read all referenced documents before implementation.

---

# Context

Repository synchronization already exists.

Pull Request synchronization already exists.

Review synchronization already exists.

This task introduces Review Comment synchronization.

The purpose is to collect reviewer comments attached to specific Pull Request changes.

These comments represent the most valuable dataset for future AI benchmarking.

---

# Architecture

Create a dedicated Review Comment synchronization module.

Do not place synchronization logic inside:

* GitHubClient
* SQLAlchemy models
* API layer

Follow separation of concerns.

---

# Supported Scope

Synchronize ReviewComment entities only.

Fields:

* github_id
* review_id
* pull_request_id
* body
* file_path
* line_number
* created_at

Use existing relationships:

Review
↓
ReviewComment

PullRequest
↓
ReviewComment

---

# File Structure

Create:

app/
└── collector/
├── services/
│   └── review_comment_sync_service.py
│
├── repositories/
│   └── review_comment_repository.py
│
└── schemas/
└── review_comment_sync_result.py

---

# Review Comment Repository

Create persistence layer.

Responsibilities:

* find by github_id
* find by review
* create comment
* update comment
* bulk lookup support

Requirements:

* SQLAlchemy only
* no business logic

---

# Review Comment Sync Service

Create:

ReviewCommentSyncService

Responsibilities:

* fetch review comments from GitHub
* synchronize comments
* update existing comments
* create missing comments

Workflow:

Pull Request
↓
GitHubClient
↓
ReviewCommentSyncService
↓
ReviewCommentRepository
↓
PostgreSQL

---

# Synchronization Rules

When comment does not exist:

* create record

When comment exists:

* update metadata

Use GitHub comment ID as synchronization key.

Prevent duplicate comments.

---

# Comment Metadata

Store:

* comment body
* file path
* line number
* review relationship
* pull request relationship
* creation timestamp

Do not remove formatting from comment body.

Store original content.

---

# Future Benchmarking Requirements

Design the implementation to support future analysis.

The following information must remain accessible:

* comment text
* file path
* line number
* review state
* pull request metadata

Future AI analysis will compare generated findings with these comments.

Do not implement benchmarking yet.

---

# Sync Modes

Support:

sync_pull_request_comments()

Synchronizes comments for a specific Pull Request.

---

Support:

sync_repository_comments()

Synchronizes comments for all Pull Requests in a repository.

Requirements:

* configurable processing limit
* suitable for historical synchronization

---

# Sync Result DTO

Create:

ReviewCommentSyncResult

Fields:

* pull_request_id
* total_processed
* created_count
* updated_count
* synchronized_at

Requirements:

* typed DTO
* no SQLAlchemy dependencies

---

# Performance Requirements

Avoid:

* N+1 database queries

Prefer:

* bulk lookups
* batched operations

The implementation should support repositories containing hundreds of thousands of comments.

Do not introduce asynchronous processing.

Do not introduce background workers.

---

# Error Handling

Handle:

PullRequestNotFound

ReviewNotFound

RepositoryNotFound

RateLimitExceeded

AuthenticationError

UnexpectedGitHubResponse

Requirements:

* structured logging
* meaningful exceptions

---

# Logging

Log:

* synchronization started
* comments fetched
* comments created
* comments updated
* synchronization completed

Do not log tokens.

Do not log full comment bodies.

---

# Testing Requirements

Create unit tests covering:

* comment creation
* comment update
* duplicate prevention
* relationship mapping
* missing review
* missing pull request
* GitHub errors

Mock:

* GitHubClient
* database layer

Do not call GitHub API.

Do not use real database.

---

# Example Usage

sync_pull_request_comments(
owner="django",
repository="django",
pull_request_number=12345
)

sync_repository_comments(
owner="numpy",
repository="numpy"
)

---

# Out of Scope

Do NOT implement:

* file change synchronization
* AI analysis
* benchmark engine
* semantic matching
* embeddings
* API endpoints
* background jobs

These will be implemented in future tasks.

---

# Acceptance Criteria

* ReviewCommentSyncService implemented
* ReviewCommentRepository implemented
* synchronization supported
* create/update workflow implemented
* duplicate prevention implemented
* relationship mapping implemented
* DTO implemented
* unit tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain synchronization workflow.
2. Explain relationship mapping strategy.
3. Explain duplicate prevention strategy.
4. Explain how future AI benchmarking will use the collected data.

Generate production-quality code only.
