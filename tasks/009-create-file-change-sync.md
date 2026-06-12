# Goal

Implement Pull Request File Change synchronization between GitHub and PostgreSQL.

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

Review Comment synchronization already exists.

This task introduces File Change synchronization.

The purpose is to collect Pull Request file changes and diffs from GitHub and store them in PostgreSQL.

These file changes will become the primary source of context for future AI analysis.

---

# Architecture

Create a dedicated File Change synchronization module.

Do not place synchronization logic inside:

* GitHubClient
* SQLAlchemy models
* API layer

Follow separation of concerns.

---

# Supported Scope

Synchronize FileChange entities only.

Fields:

* github_id (if available)
* pull_request_id
* filename
* additions
* deletions
* changes
* patch

Use existing relationship:

PullRequest
↓
FileChange

---

# File Structure

Create:

app/
└── collector/
├── services/
│   └── file_change_sync_service.py
│
├── repositories/
│   └── file_change_repository.py
│
└── schemas/
└── file_change_sync_result.py

---

# File Change Repository

Create persistence layer.

Responsibilities:

* find existing file changes
* create file change
* update file change
* remove stale file changes if necessary
* bulk lookup support

Requirements:

* SQLAlchemy only
* no business logic

---

# File Change Sync Service

Create:

FileChangeSyncService

Responsibilities:

* fetch changed files from GitHub
* synchronize file changes
* synchronize patch content
* update existing records
* create missing records

Workflow:

Pull Request
↓
GitHubClient
↓
FileChangeSyncService
↓
FileChangeRepository
↓
PostgreSQL

---

# Synchronization Rules

When file change does not exist:

* create record

When file change exists:

* update metadata

Prevent duplicates.

Use:

* pull_request_id
* filename

as synchronization key.

---

# Diff Storage

Store:

* full patch returned by GitHub

Requirements:

* preserve original formatting
* preserve line breaks
* preserve diff markers

Do not transform the patch.

Do not truncate the patch.

Future AI analysis requires the original diff.

---

# File Metadata

Store:

* filename
* additions
* deletions
* changes
* patch

Examples:

Python:

* auth.py
* models/user.py

Go:

* internal/service/payment.go
* cmd/server/main.go

JavaScript:

* api/routes.js

Do not filter by language.

---

# Large Diff Handling

Some Pull Requests may contain:

* hundreds of files
* very large patches

Requirements:

* support large payloads
* avoid excessive memory copies
* batch database operations where appropriate

Do not introduce streaming.

Do not introduce asynchronous processing.

---

# Future AI Analysis Requirements

Design the implementation so future modules can retrieve:

* Pull Request
* File Change
* Patch

efficiently.

Future AI Review Engine will use:

Pull Request
↓
FileChange.patch
↓
LLM Analysis

Do not implement AI functionality yet.

---

# Sync Modes

Support:

sync_pull_request_files()

Synchronizes files for a specific Pull Request.

---

Support:

sync_repository_files()

Synchronizes files for all Pull Requests in a repository.

Requirements:

* configurable processing limit
* suitable for historical synchronization

---

# Sync Result DTO

Create:

FileChangeSyncResult

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

The implementation should support repositories containing millions of file changes over time.

Do not optimize beyond this.

---

# Error Handling

Handle:

PullRequestNotFound

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
* files fetched
* files created
* files updated
* synchronization completed

Do not log full patch contents.

Do not log tokens.

---

# Testing Requirements

Create unit tests covering:

* file creation
* file update
* duplicate prevention
* patch persistence
* large patch handling
* missing pull request
* GitHub errors

Mock:

* GitHubClient
* database layer

Do not call GitHub API.

Do not use real database.

---

# Example Usage

sync_pull_request_files(
owner="django",
repository="django",
pull_request_number=12345
)

sync_repository_files(
owner="pandas-dev",
repository="pandas"
)

---

# Out of Scope

Do NOT implement:

* AI analysis
* embeddings
* semantic matching
* benchmark engine
* API endpoints
* background jobs
* vector databases

These will be implemented in future tasks.

---

# Acceptance Criteria

* FileChangeSyncService implemented
* FileChangeRepository implemented
* synchronization supported
* create/update workflow implemented
* duplicate prevention implemented
* patch persistence implemented
* DTO implemented
* unit tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain synchronization workflow.
2. Explain duplicate prevention strategy.
3. Explain patch storage strategy.
4. Explain how future AI analysis will consume FileChange data.

Generate production-quality code only.
