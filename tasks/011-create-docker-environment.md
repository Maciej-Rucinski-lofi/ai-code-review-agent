# Goal

Create a fully containerized local development environment using Docker and Docker Compose.

The project must not require PostgreSQL installation on the host machine.

All infrastructure services must run in containers.

The solution should support future development, testing and deployment workflows.

---

# Context

The application already contains:

* SQLAlchemy models
* Alembic migrations
* GitHub synchronization services
* CLI runner

The project currently lacks a reproducible local environment.

This task introduces Docker-based infrastructure.

---

# Architecture

Use Docker Compose.

Create containers for:

* PostgreSQL
* pgAdmin (optional but recommended)
* Application container (optional in first iteration)

The host machine should only require:

* Docker
* Docker Compose

No PostgreSQL installation on the host.

---

# File Structure

Create:

project-root/
├── docker/
│   ├── postgres/
│   │   └── init/
│   └── app/
│       └── Dockerfile
│
├── docker-compose.yml
├── .dockerignore
└── .env.example

---

# PostgreSQL Container

Use:

postgres:17

Requirements:

* persistent volume
* configurable credentials
* configurable database name
* automatic restart

Environment variables:

POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD

Expose:

5432

Volume:

postgres_data

---

# pgAdmin Container

Use:

dpage/pgadmin4

Environment variables:

PGADMIN_DEFAULT_EMAIL
PGADMIN_DEFAULT_PASSWORD

Expose:

5050

Requirements:

* persistent volume
* connect to PostgreSQL container automatically if possible

Volume:

pgadmin_data

---

# Docker Network

Create dedicated network:

pr-intelligence-network

Requirements:

* all services communicate by service names
* no hardcoded IP addresses

Example:

postgres
pgadmin
app

---

# Environment Variables

Create:

.env.example

Example:

POSTGRES_DB=pr_intelligence
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=pr_intelligence
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres

GITHUB_TOKEN=

PGADMIN_DEFAULT_EMAIL=[admin@example.com](mailto:admin@example.com)
PGADMIN_DEFAULT_PASSWORD=admin

---

# Database Configuration

The application must connect using:

DATABASE_HOST=postgres

Never use:

localhost
127.0.0.1

inside containers.

The application must be Docker-network aware.

---

# Application Container (optional for first iteration)

Prepare:

docker/app/Dockerfile

Requirements:

* Python 3.13
* install dependencies
* support CLI execution
* support Alembic commands

Do not implement production deployment.

Development container only.

---

# Developer Workflow

The following workflow must work:

Start infrastructure:

docker compose up -d

Verify containers:

docker compose ps

Run migrations:

docker compose exec app alembic upgrade head

Run synchronization:

docker compose exec app python -m app.cli.main sync-repository django django

Access PostgreSQL:

docker compose exec postgres psql -U postgres -d pr_intelligence

Access pgAdmin:

http://localhost:5050

---

# Health Checks

Add health checks for:

PostgreSQL

Requirements:

* application should wait until database becomes healthy
* future services may depend on this

---

# Persistence Requirements

Data must survive:

docker compose down

Use named volumes.

Data should only be removed via:

docker compose down -v

---

# Logging

Enable container logs.

Requirements:

* readable output
* useful for debugging
* no secrets in logs

---

# Testing Requirements

Verify:

* containers start successfully
* PostgreSQL accepts connections
* pgAdmin starts successfully
* Alembic can connect
* application can connect
* volumes persist data

---

# Out of Scope

Do NOT implement:

* Kubernetes
* Redis
* Kafka
* RabbitMQ
* production deployment
* cloud infrastructure
* monitoring stack

This task creates only a local development environment.

---

# Acceptance Criteria

* docker-compose.yml implemented
* PostgreSQL container working
* pgAdmin container working
* persistent volumes configured
* application can connect to PostgreSQL
* Alembic migrations work
* CLI commands work inside containers
* health checks implemented
* documentation added

---

# Before Implementation

Explain:

1. Container architecture
2. Networking strategy
3. Volume strategy
4. How developers should interact with PostgreSQL without installing it locally

Then generate production-quality code only.
