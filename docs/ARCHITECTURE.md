# ArbiLens Architecture

## Overview

ArbiLens is structured as a small SaaS system rather than a single web server. The important design choice is that contract handling is modeled as a staged background pipeline with persisted intermediate state.

Primary runtime components:

- Next.js frontend
- FastAPI backend API
- Postgres
- Redis
- Celery worker
- S3-compatible object storage

## Why The Architecture Looks This Way

Contract ingestion is a poor fit for request-response execution because parsing, chunking, AI calls, and report generation are slow and failure-prone.

The architecture deliberately optimizes for:

- predictable API latency
- retryable background stages
- inspectable intermediate artifacts
- clean multi-tenant boundaries
- traceable AI usage

## Processing Pipeline

The implemented pipeline is:

`upload -> store -> parse -> normalize -> extract -> score -> persist -> display`

Task chain:

`parse_document_task -> normalize_document_task -> extract_clauses_task -> analyze_risks_task`

Stage responsibilities:

- upload: validate file, store original, create `document`, `document_version`, `analysis_job`
- parse: extract raw text and structure from PDF or DOCX
- normalize: clean layout artifacts and generate chunks
- extract: identify clauses heuristically and use the OpenAI Responses API only for ambiguous chunks
- score: run deterministic risk rules and generate explanation text
- display: render persisted results in the frontend

## Storage Responsibilities

### Postgres

Stores:

- organizations and users
- documents and versions
- analysis jobs
- extracted clauses
- risk findings
- reports metadata

### Redis

Used for:

- Celery broker
- worker coordination

### Object Storage

Stores:

- uploaded source files
- generated PDF reports

The split is intentional: metadata and workflow state stay transactional in Postgres, while larger binary artifacts live in object storage.

## Why Async Workers Are Used

The backend does not parse contracts or call AI providers inside upload handlers. That work is deferred to Celery workers so the API can stay responsive and stage failures can be handled independently.

Benefits:

- users get an immediate queued response instead of a hanging upload request
- transient storage or provider failures can be retried
- the UI can poll a stable job state
- parsing and AI latency do not directly degrade API responsiveness

## AI Integration Model

The OpenAI Responses API is used for bounded, schema-validated tasks only:

- classifying ambiguous chunks into clause types
- producing concise explanation text for deterministic findings

Important constraints:

- no legacy completion-style integration
- no full-document giant prompts
- no trusting raw model output without schema validation
- no using AI output as the source of numeric risk scoring

The backend enforces schema-first handling at two layers:

- Responses API structured output schemas for model responses
- Pydantic response schemas for serialized risk, summary, and citation payloads

## Deterministic Scoring Model

Risk scoring is intentionally rule-driven.

The scoring layer owns:

- numeric score
- severity
- rule code
- recommendation baseline

The AI layer may assist with summary text, but the actual score, severity, rationale, and recommendation baseline remain deterministic and testable.

## Multi-Tenant Boundary

ArbiLens uses organization-scoped access:

- each user belongs to one organization
- documents are owned by organizations
- API reads and writes are filtered through the authenticated user organization

This is enforced through dependencies and service-level query filters rather than ad hoc checks in route handlers.

## Reliability Characteristics

Implemented hardening relevant to the current codebase:

- upload validation for extension, MIME, size, emptiness, and basic file signature
- sanitized task error recording in `analysis_jobs`
- explicit task state transitions
- retry-safe behavior for transient storage failures
- idempotent short-circuiting for already-completed later-stage tasks
- readiness checks for database, Redis, and object storage
- structured request logging with request IDs
- fallback behavior for malformed AI extraction output on a chunk

## Export And Comparison

Report generation is driven from persisted findings rather than transient frontend state. Comparison is also structured-first:

- clause presence and absence
- clause text change detection
- risk deltas
- score movement

That keeps both features explainable and auditable.

## Intentional Limitations

The architecture is realistic, but still incomplete in several areas:

- no OCR pipeline for image-only contracts
- no deep observability or metrics stack
- no webhook event-id persistence for Stripe idempotency
- no enterprise auth or SSO
- no browser-level end-to-end suite

Related docs:

- `docs/adr-productionization-next.md`
- `docs/design-decisions.md`
- `docs/reliability.md`
