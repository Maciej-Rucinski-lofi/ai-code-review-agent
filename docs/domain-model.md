# Domain Model

## Repository

Represents GitHub repository.

Fields:

- id
- owner
- name

## PullRequest

Fields:

- github_id
- title
- author
- state
- merged_at

## FileChange

Fields:

- filename
- additions
- deletions
- patch

## Review

Fields:

- reviewer
- submitted_at

## ReviewComment

Fields:

- body
- path
- line

## Analysis

Fields:

- model
- finding
- severity
- confidence

## BenchmarkResult

Fields:

- precision
- recall
- match_rate