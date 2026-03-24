# Design Decisions

This document captures the highest-value engineering choices in ArbiLens and why they were made.

## 1. Staged Background Pipeline Instead Of In-Request Processing

Decision:

- uploads create a document, version, and queued analysis job
- parsing, normalization, extraction, and scoring run in Celery workers

Why:

- contract processing is latency-heavy and failure-prone
- uploads should return quickly and predictably
- intermediate artifacts are useful for debugging, retries, and auditability

Tradeoff:

- the system is more operationally complex than a synchronous API
- state transitions and idempotency have to be designed carefully

Why this was still the right choice:

- a serious contract-analysis workflow should treat parsing and AI calls as asynchronous jobs, not request-handler work

## 2. Deterministic Scoring Owns Severity And Numeric Score

Decision:

- AI is allowed to help with extraction and concise explanation text
- the backend scoring layer owns score, severity, rule code, and recommendation baseline

Why:

- numeric risk scores need to be testable and reproducible
- explanation quality and scoring consistency are different concerns
- AI variability should not change the base risk model

Tradeoff:

- deterministic rules can be less nuanced than a human or model interpretation

Why this was still the right choice:

- explainability and reviewability matter more than model creativity in the core scoring path

## 3. Schema-First AI Integration

Decision:

- OpenAI usage is isolated behind a dedicated Responses API service
- AI outputs are validated before they can affect persistence

Why:

- malformed AI output is a normal failure mode, not an edge case
- the provider boundary should be swappable and testable
- downstream code should operate on validated structures, not raw JSON

Tradeoff:

- stricter validation rejects some usable-but-messy model responses

Why this was still the right choice:

- failure-safe behavior is more valuable than squeezing maximum recall out of brittle prompts

## 4. Chunk-Level Extraction Instead Of Whole-Document Prompting

Decision:

- extraction operates chunk by chunk after normalization

Why:

- smaller prompts reduce context noise and token usage
- chunk-level citations are easier to preserve
- the system can combine heuristics with AI only where ambiguity exists

Tradeoff:

- cross-section context can be weaker than in a full-document prompt

Why this was still the right choice:

- traceability and bounded behavior matter more here than attempting a monolithic “read the whole contract” prompt

## 5. Persist Intermediate State

Decision:

- store extracted text, chunks, clauses, risks, reports, and job-stage metadata

Why:

- failures need to be inspectable
- retries should not require starting from scratch when later stages fail
- downstream features like summary, comparison, and reports should build from persisted analysis state

Tradeoff:

- the schema becomes broader and migrations matter more

Why this was still the right choice:

- a document-analysis system is easier to reason about when each stage leaves a durable trail

## 6. Honest Scope Boundary

Decision:

- the repo includes billing, comparison, and reports, but the primary investment is still the upload-to-results path

Why:

- broad feature surfaces can easily become shallow demo code
- the strongest portfolio signal comes from depth in the hardest workflow

Tradeoff:

- some secondary features are implemented but intentionally not presented as the center of the project

Why this was still the right choice:

- it is better for the repository to be explicit about its strongest path than to over-market every implemented endpoint equally

## 7. What Was Intentionally Not Built

These omissions are deliberate, not accidental:

- no OCR pipeline for image-only contracts
- no SSO or enterprise identity integration
- no browser-level end-to-end suite yet
- no advanced observability stack
- no infrastructure-as-code beyond local Docker Compose

Those are meaningful production concerns, but they are separate from demonstrating sound application architecture and implementation judgment in this repository.
