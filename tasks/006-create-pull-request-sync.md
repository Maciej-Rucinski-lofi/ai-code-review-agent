# Goal

Implement Pull Request synchronization between GitHub and PostgreSQL.

The implementation must follow:

* docs/architecture.md
* docs/domain-model.md
* docs/tech-stack.md
* docs/github-data-model.md
* .cursor/project_context.mdc
* .cursor/engineering_standards.mdc
* .cursor/architecture_principles.mdc

Read all referenced documents before implementation.

---

# Context

Repository synchronization already exists.

GitHubClient already exists.

Database infrastructure already exists.

This task introduces historical Pull Request collection.

The purpose is to collect Pull Request metadata and store it in PostgreSQL.

This task does NOT collect:

* reviews
* review comments
* changed files

Those will be implemented later.

---

# Architecture

Create a dedicated Pull Request synchronization module.

Do not place synchronization logic inside:

* GitHubClient
* SQLAlchemy models
* API layer

Follow separation of concerns.

---

# Supported Scope

Only synchronize:

PullRequest

Fields:

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

Do not synchronize:

* reviews
* comments
* files

---

# File Structure

Create:

app/
└── collector/
├── services/
│   └── pull_request_sync_service.py
│
├── repositories/
│   └── pull_request_repository.py
│
└── schemas/
└── pull_request_sync_result.py

---

# Pull Request Repository

Create persistence layer.

Responsibilities:

* find by github_id
* find by repository + number
* create pull request
* update pull request
* bulk lookup support

Requirements:

* SQLAlchemy only
* no business logic

---

# Pull Request Sync Service

Create:

PullRequestSyncService

Responsibilities:

* fetch pull requests from GitHub
* handle pagination
* synchronize records
* update existing records
* create missing records

Workflow:

Repository
↓
GitHubClient
↓
PullRequestSyncService
↓
PullRequestRepository
↓
PostgreSQL

---

# Pagination

Support GitHub pagination.

Requirements:

* fetch multiple pages
* configurable page size
* configurable page limit

Default:

per_page = 100

Allow future full-history synchronization.

---

# Synchronization Rules

When Pull Request does not exist:

* create record

When Pull Request exists:

* update metadata

Use GitHub ID as primary synchronization key.

Do not create duplicates.

---

# Sync Modes

Support:

sync_recent_pull_requests()

Purpose:

* synchronize latest PRs

---

Support:

sync_repository_pull_requests()

Purpose:

* synchronize full repository history

Requirements:

* configurable maximum page count

---

# Sync Result DTO

Create:

PullRequestSyncResult

Fields:

* repository_id
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

The implementation should support repositories containing thousands of Pull Requests.

Do not optimize beyond this.

No async processing yet.

---

# Error Handling

Handle:

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
* page processed
* pull requests created
* pull requests updated
* synchronization completed

Do not log tokens.

---

# Testing Requirements

Create unit tests covering:

* PR creation
* PR update
* pagination
* duplicate prevention
* repository not found
* GitHub errors

Mock:

* GitHubClient
* database layer

Do not call GitHub API.

Do not use real database.

---

# Example Usage

sync_recent_pull_requests(
owner="django",
repository="django"
)

sync_repository_pull_requests(
owner="golang",
repository="go"
)

---

# Out of Scope

Do NOT implement:

* review synchronization
* review comment synchronization
* file synchronization
* AI analysis
* benchmark engine
* API endpoints
* background jobs

These will be implemented in future tasks.

---

# Acceptance Criteria

* PullRequestSyncService implemented
* PullRequestRepository implemented
* pagination supported
* create/update workflow implemented
* duplicate prevention implemented
* DTO implemented
* unit tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain synchronization workflow.
2. Explain pagination strategy.
3. Explain duplicate prevention strategy.
4. Explain how future review synchronization can build on this design.

Generate production-quality code only.
