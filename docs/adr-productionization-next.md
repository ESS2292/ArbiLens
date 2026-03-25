# ADR: What I Would Productionize Next

## Status

Proposed next steps after the current portfolio-oriented implementation.

## Context

ArbiLens already demonstrates the core product path:

- authenticated upload
- staged async processing
- clause extraction
- deterministic scoring
- persisted results
- frontend result rendering

The next productionization work should prioritize risk reduction on the main workflow rather than adding more surface area.

## Decision

Productionization should happen in this order:

## 1. Harden Auth And Session Handling

Why first:

- it affects every user-facing path
- the current browser token storage is acceptable for an MVP repo, but not a strong production posture

Scope:

- move from simple client-side token storage toward stronger session handling
- add refresh/session expiration behavior
- improve auditability around auth events

## 2. Add Browser-Level And CI Verification For The Core Workflow

Why second:

- the upload-to-results path is the product’s highest-value workflow
- stronger automated proof of that path reduces regression risk quickly

Scope:

- keep the new Playwright path
- extend it to cover one failure path
- make browser-level tests part of CI once runner/browser setup is stable

## 3. Improve Queue And Worker Observability

Why third:

- the architecture depends on asynchronous stages
- background failures are otherwise harder to detect than request failures

Scope:

- queue depth metrics
- task failure counters
- job latency visibility by stage
- clearer operational dashboards or emitted metrics

## 4. Add Webhook And Task Idempotency Persistence

Why fourth:

- idempotency matters most when external systems retry
- the repo already has some retry-safe behavior, but the remaining gaps are operational rather than architectural

Scope:

- persist processed Stripe event IDs
- expand task-attempt observability and replay safety

## 5. Strengthen Storage And Recovery Posture

Why fifth:

- uploads and reports are persisted artifacts
- a production story needs more than “store to S3-compatible storage”

Scope:

- explicit backup/retention expectations
- environment separation by bucket/prefix
- clearer recovery assumptions

## 6. Add OCR As A Deliberate Expansion, Not As A First Hardening Step

Why later:

- OCR expands document coverage, but it is not the first reliability gap in the current core workflow
- it adds cost, latency, and new operational complexity

Scope:

- image-only PDF detection
- OCR fallback stage design
- quality checks around OCR-derived text before extraction

## Consequences

This order deliberately favors:

- securing the main user boundary
- proving the main workflow continuously
- making async operations observable

It deliberately deprioritizes:

- new product surface area
- low-signal feature expansion
- infrastructure sophistication before the core workflow has stronger verification and session posture
