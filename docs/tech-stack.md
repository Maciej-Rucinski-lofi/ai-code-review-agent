# Technology Stack

## Overview

PR Intelligence Platform consists of two major responsibilities:

1. Data Collection
2. AI Analysis

The architecture should favor simplicity over scalability during the early stages.

Technology choices must be justified by maintainability and development speed.

---

# Backend

## Python

Version:
- Python 3.13+

Purpose:
- API
- AI analysis
- Benchmark engine
- Data processing

Reasoning:

Python provides the best ecosystem for:

- LLM applications
- AI experimentation
- Data analysis
- Benchmarking

Python is considered the primary language of the project.

---

# API Framework

## FastAPI

Purpose:
- REST API
- Internal endpoints
- Administrative endpoints

Reasoning:

- excellent typing support
- high performance
- automatic OpenAPI generation
- strong ecosystem

---

# Database

## PostgreSQL

Purpose:
- repositories
- pull requests
- review comments
- AI findings
- benchmark results

Reasoning:

- mature
- reliable
- supports advanced querying
- ideal for analytics

---

# ORM

## SQLAlchemy 2.x

Purpose:
- persistence layer

Requirements:

- typed mappings
- declarative models
- repository pattern

---

# Migrations

## Alembic

Purpose:
- schema versioning

Requirements:

- every schema change requires migration

---

# GitHub Integration

## GitHub REST API

Purpose:
- repository metadata
- pull requests
- reviews
- comments

Requirements:

- rate limit awareness
- retry mechanisms
- pagination support

Future:

Evaluate GraphQL API if performance becomes a concern.

---

# AI

## OpenAI

Initial model:

- GPT-5 class model

Purpose:

- pull request analysis
- finding generation
- review comparison

Requirements:

- prompts stored separately
- model abstraction layer
- provider independence

Future providers:

- Anthropic
- Google
- local models

---

# Testing

## Pytest

Requirements:

- unit tests
- integration tests
- benchmark tests

Coverage target:

- 80%+

---

# Code Quality

## Ruff

Purpose:
- linting
- formatting

Requirements:

- CI enforcement

---

## MyPy

Purpose:
- static typing

Requirements:

- strict mode

---

# Containers

## Docker

Purpose:
- local development
- deployment

Requirements:

- every service must be containerized

---

# Observability

Phase 1:

- structured logging

Phase 2:

- OpenTelemetry

Phase 3:

- Grafana
- Prometheus

---

# Frontend

Not required in MVP.

Preferred future stack:

- Next.js
- TypeScript

Purpose:

- dashboard
- benchmark visualization

---

# Future Go Components

The project may introduce Go components later.

Potential responsibilities:

- GitHub collectors
- bulk synchronization
- worker pools

Reasoning:

Go is not required until profiling proves that Python is a bottleneck.

Premature optimization should be avoided.

---

# Explicitly Rejected Technologies

For MVP do not introduce:

- Kubernetes
- Kafka
- RabbitMQ
- Microservices
- Event Sourcing
- CQRS

Reasoning:

The project should remain a modular monolith until complexity justifies expansion.