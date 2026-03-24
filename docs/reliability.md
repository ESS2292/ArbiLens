# Reliability Notes

This document describes the main failure modes considered in ArbiLens and how the current codebase handles them.

## Workflow Boundaries

Main workflow:

`register/login -> upload -> queued job -> parse -> normalize -> extract -> score -> persist -> display`

The most important reliability choice is that each expensive stage happens outside the request path and records explicit state.

## Failure Modes And Current Behavior

### Authentication And Authorization

Handled:

- invalid credentials return a clean auth error
- organization-scoped reads and writes block cross-organization document access

Current limitation:

- session handling is still MVP-grade browser token storage

### Upload Validation

Handled:

- empty uploads
- unsupported extension and MIME type
- oversized uploads
- invalid filenames
- basic content-signature mismatch for PDF and DOCX

Current limitation:

- file validation is pragmatic rather than forensic

### Object Storage Failures

Handled:

- upload uses a storage abstraction instead of direct SDK calls from routes
- storage failures are surfaced as clean application errors
- record creation and storage handoff are coordinated so failed uploads do not silently look successful

Current limitation:

- no resumable upload support

### Parser Failures

Handled:

- unreadable, corrupted, or invalid input marks the job and document as failed
- failures are sanitized before they are returned to clients

Current limitation:

- no OCR fallback for scanned/image-only PDFs

### AI Failures

Handled:

- Responses API use is isolated behind a provider service
- malformed or schema-invalid outputs fail validation
- extraction degrades safely for a chunk instead of blindly persisting bad data
- deterministic scores are not allowed to depend on AI output

Current limitation:

- explanation quality can still vary even when schema-valid

### Task Failures And Retries

Handled:

- analysis jobs store explicit status and stage fields
- later-stage tasks short-circuit when already complete
- retries are structured around stage-specific work rather than ad hoc re-entry

Current limitation:

- worker observability is still light; there is no metrics or dead-letter strategy in the repo

### Partial Analysis State

Handled:

- the frontend distinguishes queued, processing, failed, completed, and finalizing states
- results are rendered from persisted backend data rather than fake optimistic state

Current limitation:

- there is no browser-level e2e suite proving the full UI path continuously

## Operational Assumptions

The current repository assumes:

- Postgres is reachable and migrations are applied
- Redis is reachable for worker coordination
- object storage is reachable and the configured bucket exists
- OpenAI credentials are present if AI-assisted extraction/explanation paths are exercised

The readiness endpoint checks database, Redis, and object storage, but it is still a practical local-readiness check rather than a complete production health model.

## Why The Pipeline Is Easier To Trust Than A Monolithic Request

The current design improves reliability in three ways:

- failures are localized to stages
- intermediate artifacts can be inspected after a failure
- retries and idempotent guards are easier to reason about when each step has persisted state

That is the main reason the system is architected around jobs and workers instead of “upload and analyze in one request.”

## What Still Needs To Be Added For Stronger Production Reliability

- queue-depth and worker-failure metrics
- webhook event idempotency persistence
- browser-level integration coverage
- deeper storage and dependency failure observability
- more explicit backup and recovery procedures
