# Goal

Implement Pull Request Review synchronization between GitHub and PostgreSQL.

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

This task introduces Review synchronization.

The purpose is to collect Pull Request review decisions from GitHub and store them in PostgreSQL.

Examples:

* APPROVED
* CHANGES_REQUESTED
* COMMENTED

This task does NOT synchronize review comments.

Review comments will be implemented in a future task.

---

# Architecture

Create a dedicated Review synchronization module.

Do not place synchronization logic inside:

* GitHubClient
* SQLAlchemy models
* API layer

Follow separation of concerns.

---

# Supported Scope

Synchronize Review entities only.

Fields:

* github_id
* pull_request_id
* reviewer_login
* state
* submitted_at

Do not synchronize:

* review comments
* file comments

---

# File Structure

Create:

app/
└── collector/
├── services/
│   └── review_sync_service.py
│
├── repositories/
│   └── review_repository.py
│
└── schemas/
└── review_sync_result.py

---

# Review Repository

Create persistence layer.

Responsibilities:

* find by github_id
* find by pull_request
* create review
* update review
* bulk lookup support

Requirements:

* SQLAlchemy only
* no business logic

---

# Review Sync Service

Create:

ReviewSyncService

Responsibilities:

* fetch reviews from GitHub
* synchronize reviews
* update existing reviews
* create missing reviews

Workflow:

Pull Request
↓
GitHubClient
↓
ReviewSyncService
↓
ReviewRepository
↓
PostgreSQL

---

# Synchronization Rules

When review does not exist:

* create record

When review exists:

* update metadata

Use GitHub review ID as synchronization key.

Prevent duplicate reviews.

---

# Review States

Support all GitHub review states.

Examples:

* APPROVED
* CHANGES_REQUESTED
* COMMENTED
* DISMISSED
* PENDING

Do not hardcode known values.

Store the value received from GitHub.

---

# Sync Modes

Support:

sync_pull_request_reviews()

Synchronizes all reviews for a specific Pull Request.

---

Support:

sync_repository_reviews()

Synchronizes reviews for all Pull Requests in a repository.

Requirements:

* configurable processing limit
* suitable for historical synchronization

---

# Sync Result DTO

Create:

ReviewSyncResult

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

The implementation should support repositories containing thousands of reviews.

Do not optimize beyond this.

No async processing yet.

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
* reviews fetched
* reviews created
* reviews updated
* synchronization completed

Do not log tokens.

---

# Testing Requirements

Create unit tests covering:

* review creation
* review update
* duplicate prevention
* review state synchronization
* pull request not found
* GitHub errors

Mock:

* GitHubClient
* database layer

Do not call GitHub API.

Do not use real database.

---

# Example Usage

sync_pull_request_reviews(
owner="django",
repository="django",
pull_request_number=12345
)

sync_repository_reviews(
owner="golang",
repository="go"
)

---

# Out of Scope

Do NOT implement:

* review comments synchronization
* file change synchronization
* AI analysis
* benchmark engine
* API endpoints
* background jobs

These will be implemented in future tasks.

---

# Acceptance Criteria

* ReviewSyncService implemented
* ReviewRepository implemented
* review synchronization supported
* create/update workflow implemented
* duplicate prevention implemented
* DTO implemented
* unit tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain synchronization workflow.
2. Explain duplicate prevention strategy.
3. Explain review state handling.
4. Explain how review comments will extend this design in future tasks.

Generate production-quality code only.
