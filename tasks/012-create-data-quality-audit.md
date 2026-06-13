# Goal

Implement a Data Quality Audit module that validates the integrity, completeness and consistency of collected GitHub data.

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

The data collection pipeline is now capable of synchronizing:

* Repositories
* Pull Requests
* Reviews
* Review Comments
* File Changes

Before building AI analysis capabilities, the project must verify that collected data is complete and internally consistent.

This task introduces a dedicated Data Quality Audit module.

---

# Architecture

Create a dedicated audit module.

Do not place audit logic inside:

* GitHubClient
* Sync Services
* SQLAlchemy Models
* API Layer

Follow separation of concerns.

---

# File Structure

Create:

app/
└── audit/
├── services/
│   └── data_quality_audit_service.py
│
├── repositories/
│   └── audit_repository.py
│
└── schemas/
├── audit_result.py
├── audit_issue.py
└── audit_summary.py

---

# Audit Categories

Implement the following audit categories.

---

## Referential Integrity Audit

Validate:

* PullRequest.repository_id exists
* Review.pull_request_id exists
* ReviewComment.review_id exists
* ReviewComment.pull_request_id exists
* FileChange.pull_request_id exists
* Analysis.pull_request_id exists
* BenchmarkResult.analysis_id exists

Report all orphaned records.

---

## Duplicate Detection Audit

Validate:

Repository:

* github_id unique

PullRequest:

* github_id unique

Review:

* github_id unique

ReviewComment:

* github_id unique

FileChange:

* pull_request_id + filename unique

Report all duplicates.

---

## Missing Data Audit

Detect:

Repositories:

* missing owner
* missing name

Pull Requests:

* missing title
* missing state

Reviews:

* missing reviewer_login
* missing state

Review Comments:

* empty body
* missing file path

File Changes:

* missing filename
* missing patch

Report all findings.

---

## Completeness Audit

Generate statistics:

* repositories count
* pull requests count
* reviews count
* review comments count
* file changes count

Additional metrics:

* PRs without reviews
* Reviews without comments
* PRs without file changes

---

## Timestamp Audit

Validate:

* created_at <= updated_at
* merged_at >= created_at

Report invalid records.

---

## GitHub Identifier Audit

Validate:

* github_id is present
* github_id > 0

For:

* Repository
* PullRequest
* Review
* ReviewComment

Report invalid records.

---

# Audit Service

Create:

DataQualityAuditService

Responsibilities:

* execute all audit categories
* aggregate findings
* produce summary

Workflow:

Database
↓
Audit Repository
↓
DataQualityAuditService
↓
Audit Summary

---

# Audit Result Models

Create:

AuditIssue

Fields:

* category
* entity_type
* entity_id
* description
* severity

Severity:

* INFO
* WARNING
* ERROR

---

Create:

AuditSummary

Fields:

* total_entities_checked
* total_issues
* info_count
* warning_count
* error_count

---

Create:

AuditResult

Fields:

* summary
* issues

---

# Logging

Log:

* audit started
* category execution
* category results
* audit completed

Do not log large datasets.

Do not log patch contents.

---

# Performance Requirements

The audit should support:

* millions of file changes
* hundreds of thousands of reviews
* large repositories

Requirements:

* aggregate queries preferred
* avoid N+1 queries

No caching required.

No async processing required.

---

# Testing Requirements

Create unit tests covering:

* duplicate detection
* orphan detection
* missing data detection
* timestamp validation
* summary generation

Use mocked repositories.

Do not use real database.

---

# Example Usage

run_full_audit()

run_referential_integrity_audit()

run_duplicate_audit()

run_completeness_audit()

---

# Out of Scope

Do NOT implement:

* automatic data repair
* AI analysis
* benchmark engine
* dashboards
* API endpoints
* background jobs

This task only reports issues.

---

# Acceptance Criteria

* DataQualityAuditService implemented
* all audit categories implemented
* audit DTOs implemented
* issue reporting implemented
* summary reporting implemented
* unit tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain audit architecture.
2. Explain audit category design.
3. Explain scalability considerations.
4. Explain how audit results will support future AI benchmarking.

Generate production-quality code only.
