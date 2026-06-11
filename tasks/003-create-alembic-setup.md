# Goal

Set up database infrastructure and Alembic migration support for the PR Intelligence Platform.

The implementation must follow:

* docs/architecture.md
* docs/tech-stack.md
* .cursor/project_context.mdc
* .cursor/engineering_standards.mdc
* .cursor/architecture_principles.mdc

Read all referenced documents before implementation.

---

# Context

Database models already exist.

This task focuses on:

* database configuration
* SQLAlchemy session management
* engine creation
* Alembic configuration
* initial migration generation support

No business logic should be implemented.

No GitHub integration should be implemented.

No API endpoints should be implemented.

---

# Requirements

Use:

* PostgreSQL
* SQLAlchemy 2.x
* Alembic

Create database infrastructure that supports:

* local development
* future testing
* future Docker deployment

---

# Create Database Configuration

Create:

app/database/config.py

Responsibilities:

* load environment variables
* build database URL
* expose database settings

Use environment variables:

DATABASE_HOST
DATABASE_PORT
DATABASE_NAME
DATABASE_USER
DATABASE_PASSWORD

Provide sensible defaults for local development.

---

# Create Database Engine

Create:

app/database/engine.py

Responsibilities:

* create SQLAlchemy engine
* expose session factory

Requirements:

* SQLAlchemy 2.x style
* future-proof configuration
* proper connection pooling configuration

---

# Create Session Management

Create:

app/database/session.py

Responsibilities:

* session factory
* session dependency helper

Requirements:

* type-safe
* reusable
* suitable for FastAPI integration later

---

# Configure Alembic

Create:

alembic.ini

Configure:

* migration path
* database URL loading strategy

Create:

alembic/env.py

Requirements:

* use application settings
* auto-discover metadata
* support autogenerate

Alembic must use the metadata from the SQLAlchemy models.

---

# Create Initial Migration

Generate:

Initial migration containing all current models.

The migration must create:

* repositories
* pull_requests
* file_changes
* reviews
* review_comments
* analyses
* benchmark_results

All foreign keys and indexes must be included.

---

# Docker Compatibility

Database configuration must support future Docker Compose usage.

Do not hardcode local paths.

Use environment variables.

---

# Testing Requirements

Create basic tests verifying:

* database settings load correctly
* engine creation succeeds
* session factory can create sessions

No integration tests against a live database yet.

---

# File Structure

Expected additions:

app/
└── database/
    ├── config.py
    ├── engine.py
    ├── session.py

alembic/
├── env.py
├── versions/

alembic.ini

---

# Out of Scope

Do NOT implement:

* repository pattern
* GitHub API integration
* business services
* FastAPI endpoints
* AI modules
* benchmark engine

---

# Acceptance Criteria

* Alembic initialized correctly
* autogenerate works
* metadata discovered automatically
* migration creates all tables
* Ruff passes
* MyPy passes
* project starts without errors

Before generating code:

1. Explain the database infrastructure design.
2. Explain how Alembic discovers models.
3. Explain how future migrations will be created.
4. Identify any risks or improvements.

Generate production-quality code only.
