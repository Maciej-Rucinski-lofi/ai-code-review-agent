# PR Intelligence Platform

A research and engineering platform that collects historical pull requests from large open source repositories and benchmarks AI-generated code review findings against real human reviews.

**This is not a GitHub bot.** The platform does not post comments to public repositories. It focuses on offline data collection, analysis, and benchmarking.

## Goals

- Collect pull requests, review comments, diffs, and metadata from major open source projects
- Perform AI-assisted analysis on collected changes
- Compare AI findings with human review comments
- Build reusable benchmark datasets for evaluating review quality

## Target Repositories

- [django/django](https://github.com/django/django)
- [pandas-dev/pandas](https://github.com/pandas-dev/pandas)
- [numpy/numpy](https://github.com/numpy/numpy)
- [golang/go](https://github.com/golang/go)
- [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes)

## Architecture

The system is a modular monolith organized around clear separation of concerns:

```
GitHub API
    ↓
Collector
    ↓
PostgreSQL
    ↓
Analysis Engine
    ↓
Benchmark
```

| Module | Responsibility |
|--------|----------------|
| `collector/` | GitHub API integration and data synchronization |
| `database/` | SQLAlchemy models, sessions, and migrations |
| `analysis/` | Pull request analysis and finding generation |
| `benchmark/` | AI vs. human review comparison and metrics |
| `api/` | REST endpoints (planned) |

Dependency direction flows inward: API and services depend on domain logic, which depends on infrastructure abstractions — not the reverse.

See [docs/architecture.md](docs/architecture.md) for the full phased design.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12+ |
| API | FastAPI (planned) |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| HTTP client | httpx |
| Testing | pytest |
| Linting | Ruff |
| Type checking | mypy (strict) |

## Project Structure

```
app/
├── api/              # REST API layer
├── collector/        # GitHub integration and sync services
│   ├── github/       # API client, models, exceptions
│   ├── repositories/ # Persistence repositories
│   ├── schemas/      # Sync result DTOs
│   └── services/     # Synchronization orchestration
├── analysis/         # AI analysis engine
├── benchmark/        # Review benchmarking
└── database/         # Models, engine, session management

alembic/              # Database migrations
docs/                 # Architecture and design documentation
tasks/                # Implementation task specifications
tests/                # Unit tests (no live GitHub calls)
```

## Getting Started

### Prerequisites

- Python 3.12 or later
- PostgreSQL 14 or later
- A GitHub personal access token (recommended for higher rate limits)

### Installation

```bash
git clone <repository-url>
cd ai-code-review-agent

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### Configuration

Set environment variables for database and GitHub access:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_HOST` | `localhost` | PostgreSQL host |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_NAME` | `pr_intelligence` | Database name |
| `DATABASE_USER` | `postgres` | Database user |
| `DATABASE_PASSWORD` | `postgres` | Database password |
| `GITHUB_TOKEN` | — | GitHub personal access token |
| `GITHUB_API_BASE_URL` | `https://api.github.com` | GitHub API base URL |
| `GITHUB_TIMEOUT_SECONDS` | `30` | HTTP request timeout |
| `GITHUB_MAX_RETRIES` | `3` | Retry count for transient errors |

Example:

```bash
export DATABASE_HOST=localhost
export DATABASE_NAME=pr_intelligence
export GITHUB_TOKEN=ghp_your_token_here
```

### Database Setup

Create the database, then apply migrations:

```bash
createdb pr_intelligence
alembic upgrade head
```

## Development

### Run Tests

```bash
pytest
```

All unit tests mock external services — no live GitHub API calls are made during testing.

### Lint and Format

```bash
ruff check .
ruff format .
```

### Type Check

```bash
mypy app
```

## Current Status

| Component | Status |
|-----------|--------|
| Project structure | Done |
| Database models and migrations | Done |
| GitHub REST client (pagination, retries, rate limits) | Done |
| Repository synchronization | Done |
| Pull request synchronization | In progress |
| Review and comment collection | Planned |
| AI analysis engine | Planned |
| Benchmarking | Planned |
| REST API and dashboard | Planned |

See [docs/roadmap.md](docs/roadmap.md) for the full release plan.

## Documentation

| Document | Description |
|----------|-------------|
| [Vision](docs/vision.md) | Long-term goals and research direction |
| [Architecture](docs/architecture.md) | System design and phased rollout |
| [Domain Model](docs/domain-model.md) | Core entities and relationships |
| [Tech Stack](docs/tech-stack.md) | Technology choices and rationale |
| [Benchmark Strategy](docs/benchmark-strategy.md) | AI vs. human review evaluation |
| [Development Workflow](docs/development-workflow.md) | Contribution process |
| [Non-Goals](docs/non-goals.md) | Explicit scope boundaries |

## Non-Goals

The platform will not:

- Comment on or modify GitHub pull requests
- Deploy as a real-time GitHub bot
- Introduce microservices, Kubernetes, or message queues in the MVP
- Perform automated code generation

## License

License not yet specified.
