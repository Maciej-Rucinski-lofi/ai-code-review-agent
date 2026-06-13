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
| Language | Python 3.12+ (3.13 in Docker app container) |
| API | FastAPI (planned) |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| HTTP client | httpx |
| Local environment | Docker Compose |
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
docker/               # Docker Compose infrastructure
│   ├── app/          # Application container Dockerfile
│   ├── postgres/     # PostgreSQL init scripts
│   └── pgadmin/      # pgAdmin server auto-registration
docs/                 # Architecture and design documentation
tasks/                # Implementation task specifications
tests/                # Unit tests (no live GitHub calls)
```

## Getting Started

### Prerequisites

Choose one setup path:

**Docker (recommended)** — no local PostgreSQL required:

- Docker and Docker Compose
- A GitHub personal access token (recommended for higher rate limits)

**Local Python** — for running tests and linting on the host:

- Python 3.12 or later
- PostgreSQL 14 or later (or use Docker for the database only)
- A GitHub personal access token (recommended for higher rate limits)

### Docker Development Environment

The project includes a fully containerized local development environment. You do **not** need PostgreSQL installed on your host machine — only Docker and Docker Compose.

#### Container Architecture

Three services run on a dedicated bridge network (`pr-intelligence-network`):

| Service | Image | Purpose |
|---------|-------|---------|
| `postgres` | `postgres:17` | Primary database with health checks |
| `pgadmin` | `dpage/pgadmin4` | Web UI for browsing and querying the database |
| `app` | Built from `docker/app/Dockerfile` | Python 3.13 dev container for Alembic migrations and CLI commands |

The `app` container stays running in the background (`tail -f /dev/null`) so you can execute commands with `docker compose exec`.

PostgreSQL exposes a health check (`pg_isready`). The `app` and `pgadmin` services wait until the database is healthy before starting.

#### Networking

All services communicate by **service name** on `pr-intelligence-network`. No hardcoded IP addresses are used.

| Service | Host (inside containers) | Host (from your machine) |
|---------|--------------------------|--------------------------|
| PostgreSQL | `postgres:5432` | `localhost:5432` |
| pgAdmin | — | [http://localhost:5050](http://localhost:5050) |

Inside containers, always use `DATABASE_HOST=postgres` — never `localhost` or `127.0.0.1`.

The application reads connection settings from environment variables (see [Configuration](#configuration)). Copy the example file and adjust values if needed:

```bash
cp .env.example .env
```

Docker-specific variables in `.env.example`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `pr_intelligence` | Database created on first startup |
| `POSTGRES_USER` | `postgres` | PostgreSQL superuser |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `DATABASE_HOST` | `postgres` | Hostname used by the app container |
| `PGADMIN_DEFAULT_EMAIL` | `admin@example.com` | pgAdmin login email |
| `PGADMIN_DEFAULT_PASSWORD` | `admin` | pgAdmin login password |

#### Volumes and Persistence

Named volumes persist data across `docker compose down`:

| Volume | Purpose |
|--------|---------|
| `postgres_data` | PostgreSQL data files |
| `pgadmin_data` | pgAdmin settings and state |

Data survives container restarts and `docker compose down`. To remove containers **and** volumes:

```bash
docker compose down -v
```

Optional PostgreSQL init scripts can be placed in `docker/postgres/init/`. pgAdmin auto-registers the PostgreSQL server via `docker/pgadmin/servers.json`.

#### Quick Start

Start all services:

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Expected status: `postgres` is **healthy**, `pgadmin` and `app` are **up**.

Apply migrations inside the app container:

```bash
docker compose exec app alembic upgrade head
```

Run CLI commands (example: sync a repository):

```bash
docker compose exec app python -m app.cli.main sync-repository django django
```

Check collection statistics:

```bash
docker compose exec app python -m app.cli.main stats
```

#### Accessing PostgreSQL Without a Local Install

Use any of these options — no host PostgreSQL required:

**psql inside the container:**

```bash
docker compose exec postgres psql -U postgres -d pr_intelligence
```

**pgAdmin web UI:**

1. Open [http://localhost:5050](http://localhost:5050)
2. Sign in with `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` from `.env`
3. The server **PR Intelligence PostgreSQL** is pre-configured and connects via the Docker network

**Application CLI** (runs queries through SQLAlchemy):

```bash
docker compose exec app python -m app.cli.main stats
```

#### Lifecycle Commands

Stop containers (data persists):

```bash
docker compose down
```

View container logs:

```bash
docker compose logs postgres
docker compose logs pgadmin
docker compose logs app
```

Rebuild after dependency changes:

```bash
docker compose up -d --build
```

### Local Installation

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

With Docker running, migrations are applied via the app container (see [Docker Development Environment](#docker-development-environment)).

For a local PostgreSQL installation, create the database and apply migrations:

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
| Docker development environment | Done |
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
