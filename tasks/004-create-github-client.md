# Goal

Create a reusable GitHub API client module.

The implementation must follow:

* docs/architecture.md
* docs/tech-stack.md
* .cursor/project_context.mdc
* .cursor/engineering_standards.mdc
* .cursor/architecture_principles.mdc

Read all referenced documents before implementation.

---

# Context

The project collects historical Pull Requests from large open source repositories.

This task only creates the GitHub API integration layer.

No synchronization logic should be implemented.

No database persistence should be implemented.

No AI analysis should be implemented.

---

# Requirements

Use:

* GitHub REST API
* httpx

The implementation must support:

* authenticated requests
* unauthenticated requests
* pagination
* rate limit awareness
* retries
* timeout configuration

The GitHub client must be reusable by future collector services.

---

# Configuration

Create:

app/collector/config.py

Environment variables:

GITHUB_TOKEN

Requirements:

* token optional
* authenticated requests when token exists
* anonymous requests otherwise

---

# Client Structure

Create:

app/collector/github/

Structure:

github/
├── client.py
├── exceptions.py
├── models.py
└── **init**.py

---

# GitHub Client

Create:

GitHubClient

Responsibilities:

* perform requests
* build URLs
* manage headers
* manage authentication
* handle pagination
* handle rate limits

Requirements:

* use httpx
* configurable timeout
* configurable retries

Do not implement business logic.

Client must only expose GitHub operations.

---

# Supported Operations

Implement methods:

## Repository

get_repository(
owner: str,
name: str
)

Returns repository metadata.

---

## Pull Requests

get_pull_requests(
    owner: str,
    repository: str,
    state: str,
    page: int
)

Returns Pull Request list.

---

## Pull Request Details

get_single_pull_request(
    owner: str,
    repository: str,
    pull_request_number: int
)

Returns single Pull Request.

---

## Reviews

get_reviews(
    owner: str,
    repository: str,
    pull_request_number: int
)

Returns reviews.

---

## Review Comments

get_review_comments(
    owner: str,
    repository: str,
    pull_request_number: int
)

Returns review comments.

---

## Files

get_pull_request_files(
    owner: str,
    repository: str,
    pull_request_number: int
)

Returns changed files and patches.

---

# Error Handling

Create custom exceptions:

GitHubError

RateLimitExceeded

AuthenticationError

RepositoryNotFound

PullRequestNotFound

Requirements:

* meaningful error messages
* preserve original response information

---

# DTO Models

Create typed DTOs representing:

Repository

PullRequest

Review

ReviewComment

FileChange

Requirements:

* separate from SQLAlchemy entities
* used only by GitHub integration layer

Do not reuse database models.

---

# Pagination

Support GitHub pagination.

Requirements:

* parse Link header
* expose helper methods
* allow future bulk synchronization

Do not implement bulk sync logic yet.

---

# Rate Limiting

Detect:

* remaining requests
* reset time

Requirements:

* log warnings
* raise dedicated exception when limit exceeded

Do not automatically sleep.

---

# Logging

Implement structured logging for:

* requests
* responses
* rate limit information

Do not log tokens.

---

# Testing Requirements

Create unit tests using mocked HTTP responses.

Verify:

* authentication
* pagination
* repository retrieval
* pull request retrieval
* exception handling

No real GitHub requests.

No integration tests yet.

---

# File Structure

Expected additions:

app/
└── collector/
├── config.py
└── github/
├── client.py
├── exceptions.py
├── models.py
└── **init**.py

tests/
└── collector/
└── github/

---

# Out of Scope

Do NOT implement:

* repository synchronization
* pull request synchronization
* database persistence
* AI analysis
* benchmarking
* FastAPI endpoints

These will be implemented in future tasks.

---

# Acceptance Criteria

* GitHubClient implemented
* authentication supported
* pagination supported
* rate limit detection supported
* DTO models implemented
* custom exceptions implemented
* unit tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain proposed GitHub client architecture.
2. Explain separation between DTOs and database models.
3. Explain pagination handling strategy.
4. Explain rate limit handling strategy.

Generate production-quality code only.
