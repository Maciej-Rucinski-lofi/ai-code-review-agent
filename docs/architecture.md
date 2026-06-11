# Architecture

## Phase 1

Historical Pull Request Collection

GitHub API
↓
Collector
↓
PostgreSQL

## Phase 2

Review Analysis

Database
↓
Analysis Engine
↓
Findings

## Phase 3

AI Review

Diff
↓
LLM
↓
Review Findings

## Phase 4

Benchmarking

AI Findings
vs
Human Review Comments

Metrics:

- precision
- recall
- match rate