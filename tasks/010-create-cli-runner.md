# Goal

Create a Command Line Interface (CLI) for executing synchronization workflows and operational tasks.

The implementation must follow:

* docs/architecture.md
* docs/tech-stack.md
* docs/domain-model.md
* .cursor/project_context.mdc
* .cursor/engineering_standards.mdc
* .cursor/architecture_principles.mdc

Read all referenced documents before implementation.

---

# Context

The project already contains:

* database models
* database infrastructure
* GitHub client
* repository synchronization
* pull request synchronization
* review synchronization
* review comment synchronization
* file change synchronization

There is currently no application entry point.

This task introduces a CLI layer that allows operators and developers to execute synchronization workflows.

---

# Architecture

Create a dedicated CLI module.

Do not place CLI logic inside:

* Sync Services
* GitHub Client
* Database Models
* Repository Layer

The CLI must orchestrate existing services.

Follow separation of concerns.

---

# Technology

Use:

* Typer

Requirements:

* typed commands
* automatic help generation
* clean command hierarchy

Do not use argparse.

---

# File Structure

Create:

app/
├── cli/
│   ├── main.py
│   ├── commands/
│   │   ├── repository.py
│   │   ├── pull_request.py
│   │   ├── review.py
│   │   ├── review_comment.py
│   │   ├── file_change.py
│   │   └── stats.py
│   │
│   └── dependencies.py

---

# Entry Point

Support:

python -m app.cli.main

Requirements:

* application startup
* dependency wiring
* command registration

---

# Repository Commands

Implement:

sync-repository

Example:

python -m app.cli.main sync-repository django django

Parameters:

* owner
* repository

Workflow:

CLI
↓
RepositorySyncService
↓
GitHub
↓
Database

Display:

* repository name
* synchronization result
* execution time

---

# Pull Request Commands

Implement:

sync-prs

Example:

python -m app.cli.main sync-prs django django

Parameters:

* owner
* repository
* max-pages (optional)

Workflow:

CLI
↓
PullRequestSyncService

Display:

* total processed
* created
* updated
* execution time

---

# Review Commands

Implement:

sync-reviews

Example:

python -m app.cli.main sync-reviews django django

Parameters:

* owner
* repository

Workflow:

CLI
↓
ReviewSyncService

Display summary.

---

# Review Comment Commands

Implement:

sync-comments

Example:

python -m app.cli.main sync-comments django django

Parameters:

* owner
* repository

Workflow:

CLI
↓
ReviewCommentSyncService

Display summary.

---

# File Change Commands

Implement:

sync-files

Example:

python -m app.cli.main sync-files django django

Parameters:

* owner
* repository

Workflow:

CLI
↓
FileChangeSyncService

Display summary.

---

# Statistics Command

Implement:

stats

Example:

python -m app.cli.main stats

Display:

Repositories: X
Pull Requests: X
Reviews: X
Review Comments: X
File Changes: X

Requirements:

* read-only operation
* database only

---

# Error Handling

Handle:

* invalid repository
* GitHub authentication errors
* rate limits
* database connection errors
* unexpected failures

Requirements:

* user-friendly output
* non-zero exit codes on failure

Do not expose stack traces by default.

---

# Logging

CLI should:

* display progress information
* display execution duration
* display synchronization summary

Do not display secrets.

Do not display GitHub tokens.

---

# Dependency Injection

Create CLI dependency helpers.

Requirements:

* centralized service creation
* centralized configuration loading

Avoid:

* creating services directly inside commands

---

# Testing Requirements

Create tests covering:

* command registration
* command execution
* argument validation
* service invocation
* error handling

Mock:

* sync services
* database layer
* GitHub layer

Do not call GitHub API.

Do not use real database.

---

# Example Usage

Repository:

python -m app.cli.main sync-repository django django

Pull Requests:

python -m app.cli.main sync-prs django django --max-pages 10

Reviews:

python -m app.cli.main sync-reviews django django

Comments:

python -m app.cli.main sync-comments django django

Files:

python -m app.cli.main sync-files django django

Statistics:

python -m app.cli.main stats

---

# Out of Scope

Do NOT implement:

* FastAPI endpoints
* Web UI
* Dashboard
* Background jobs
* Scheduling
* AI analysis
* Benchmarking

This task only creates the CLI execution layer.

---

# Acceptance Criteria

* CLI application implemented
* Typer integrated
* all commands registered
* dependency injection implemented
* statistics command implemented
* error handling implemented
* tests passing
* Ruff passing
* MyPy passing

Before generating code:

1. Explain CLI architecture.
2. Explain command organization.
3. Explain dependency injection strategy.
4. Explain how future audit and AI commands can be added.

Generate production-quality code only.
