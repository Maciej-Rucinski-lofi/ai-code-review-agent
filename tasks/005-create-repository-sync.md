# Goal

Implement repository synchronization between GitHub and PostgreSQL.

The implementation must follow:

* docs/architecture.md
* docs/domain-model.md
* docs/tech-stack.md
* .cursor/project_context.mdc
* .cursor/engineering_standards.mdc
* .cursor/architecture_principles.mdc

Read all referenced documents before implementation.

---

# Context

The GitHub client already exists.

Database models already exist.

Database infrastructure already exists.

This task introduces the first synchronization workflow.

The purpose is to synchronize repository metadata from GitHub into PostgreSQL.

---

# Requirements

Supported repositories:

Examples:

* django/django
* pandas-dev/pandas
* numpy/numpy
* golang/go
* kubernetes/kubernetes

Repository synchronization must work for any public repository.

---

# Architecture

Create a dedicated repository synchronization module.

Do not place synchronization logic inside:

* GitHubClient
* SQLAlchemy models
* API layer

Follow separation of concerns.

---

# File Structure

Create:

app/
└── collector/
├── services/
│   └── repository_sync_service.py
│
├── repositories/
│   └── repository_repository.py
│
└── schemas/
└── repository_sync_result.py

---

# Repository Repository

Create a persistence layer responsible for Repository entities.

Responsibilities:

* find by github_id
* find by owner/name
* create repository
* update repository

Requirements:

* SQLAlchemy only
* no business logic

---

# Repository Sync Service

Create:

RepositorySyncService

Responsibilities:

* fetch repository from GitHub
* determine create vs update
* persist repository
* return synchronization result

Workflow:

GitHub
↓
GitHubClient
↓
RepositorySyncService
↓
RepositoryRepository
↓
PostgreSQL

---

# Synchronization Rules

When repository does not exist:

* create new record

When repository already exists:

* update metadata

Tracked fields:

* github_id
* owner
* name
* description
* default_branch

Do not overwrite internal identifiers.

---

# Sync Result DTO

Create:

RepositorySyncResult

Fields:

* repository_id
* github_id
* action
* synchronized_at

Action values:

* created
* updated

Requirements:

* typed DTO
* no SQLAlchemy dependencies

---

# Error Handling

Handle:

RepositoryNotFound

AuthenticationError

RateLimitExceeded

UnexpectedGitHubResponse

Requirements:

* meaningful errors
* structured logging

---

# Logging

Log:

* synchronization started
* repository fetched
* repository created
* repository updated
* synchronization completed

Do not log tokens.

---

# Testing Requirements

Create unit tests covering:

* repository creation
* repository update
* repository not found
* GitHub errors

Mock:

* GitHubClient
* database session

Do not call GitHub API.

Do not use real database.

---

# Example Usage

The service should support:

sync_repository(
owner="django",
repository="django"
)

sync_repository(
owner="golang",
repository="go"
)

---

# Out of Scope

Do NOT implement:

* pull request synchronization
* review synchronization
* review comments synchronization
* AI analysis
* benchmarking
* API endpoints
* background jobs

These will be implemented in future tasks.

---

# Acceptance Criteria

* RepositorySyncService implemented
* RepositoryRepository implemented
* repository create/update supported
* DTOs implemented
* unit tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain service architecture.
2. Explain repository pattern implementation.
3. Explain synchronization workflow.
4. Identify potential future extension points.

Generate production-quality code only.
