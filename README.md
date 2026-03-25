# ArbiLens

[![CI](https://github.com/ESS2292/ArbiLens/actions/workflows/ci.yml/badge.svg)](https://github.com/ESS2292/ArbiLens/actions/workflows/ci.yml)

ArbiLens is a contract review application that combines deterministic risk scoring with AI-assisted clause extraction and explanation.

The repository is intentionally built as a monorepo with a real application shape:

- `frontend/`: Next.js App Router UI
- `backend/`: FastAPI API, worker tasks, SQLAlchemy models, Alembic migrations
- `infra/`: Docker Compose for local development
- `docs/`: architecture, development, and deployment notes

This is a serious implementation exercise, not a polished commercial product. The codebase is designed to demonstrate backend service design, async job orchestration, typed API integration, multi-tenant boundaries, and pragmatic AI integration without pretending the system is production-complete.

## What ArbiLens Does

ArbiLens accepts a contract upload, stores the original file, parses and normalizes the text in background workers, extracts clause candidates, applies deterministic risk rules, and exposes structured results through an authenticated UI and API.

Supported source formats today:

- PDF
- DOCX

Primary outputs:

- processing status
- extracted clauses
- deterministic risk findings
- document-level summary
- PDF export
- contract comparison

The core workflow in this repository is contract ingestion through structured results. Report export, comparison, and billing are implemented, but they are secondary to that main path and should be read that way.

## What This Project Demonstrates

- Service-oriented FastAPI backend design with thin route handlers
- Async document-processing pipeline using Celery and Redis
- SQLAlchemy data modeling for multi-tenant SaaS workflows
- S3-compatible object storage abstraction
- OpenAI Responses API integration with schema validation and failure handling
- Deterministic scoring separated from AI-generated explanation text
- Typed frontend API integration with status polling and failure-state handling
- Practical test coverage around auth, uploads, parsing, extraction, scoring, reports, and workflow failures

## Verification Status

Last repository verification pass: March 24, 2026.

Verified directly in this repository:

- backend source compiles cleanly with `python3 -m compileall backend/app backend/alembic`
- local startup flows are documented for Docker Compose and split local services
- GitHub Actions CI is configured to run backend tests plus frontend typechecks and tests on push and pull request

Not verified in this repository snapshot:

- browser-level end-to-end UI automation in CI
- a live production deployment target

There is now a browser-level Playwright path in `frontend/e2e/auth-upload-results.spec.ts`, but it is intended as a local verification path first and is not yet part of CI.

## Architecture

Core services:

- `frontend`: Next.js App Router application for login, dashboard, uploads, document results, comparison, billing, and report actions
- `backend`: FastAPI API with versioned routes under `/api/v1`
- `postgres`: durable storage for users, organizations, documents, versions, jobs, clauses, risks, and reports
- `redis`: Celery broker and worker coordination
- `worker`: Celery task runner for parsing, normalization, extraction, and scoring
- `object storage`: stores uploaded source files and generated PDF reports

The repo is organized around clear boundaries:

- request handling in API routes
- business logic in services
- persistence in models and migrations
- background processing in task modules
- UI state and API calls in typed frontend modules

More detail: `docs/architecture.md`

Related engineering notes:

- `docs/adr-productionization-next.md`
- `docs/design-decisions.md`
- `docs/reliability.md`

## Repository Map

If you are reviewing the codebase quickly, these are the highest-signal paths:

- `backend/app/services/documents.py`: upload validation, storage handoff, document/version/job creation
- `backend/app/tasks/document_tasks.py`: async pipeline orchestration and stage transitions
- `backend/app/services/extraction.py`: hybrid heuristics + AI clause extraction with schema validation
- `backend/app/services/scoring.py`: deterministic risk rubric and citation generation
- `backend/app/tests/test_pipeline.py`: end-to-end workflow coverage for PDF and DOCX processing
- `frontend/lib/api/client.ts`: typed frontend API boundary
- `frontend/components/documents/document-results.tsx`: result-state handling for queued, failed, and completed analysis

## Processing Pipeline

The contract workflow is staged explicitly:

`upload -> store -> parse -> normalize -> extract -> score -> persist -> display`

Concrete task flow:

`parse_document_task -> normalize_document_task -> extract_clauses_task -> analyze_risks_task`

What happens at each step:

1. Upload validates extension, MIME type, size, emptiness, and basic file signature.
2. The original file is stored in object storage and linked to a `document_version`.
3. A queued `analysis_job` is created.
4. Parsing extracts raw text and structured sections.
5. Normalization cleans text and persists chunks suitable for downstream analysis.
6. Clause extraction uses heuristics first and the OpenAI Responses API second for ambiguous chunks.
7. Deterministic rules create risk scores and severities.
8. The frontend polls status and then renders stored results.

## Why Async Workers Are Used

Parsing, normalization, AI calls, and export generation are all slow or failure-prone compared with standard request-response API work.

Moving those stages into workers gives the system better behavior:

- uploads return quickly
- failures are isolated to a stage
- stages can be retried
- intermediate artifacts can be inspected
- API responsiveness does not depend on parsing or AI latency

This is a deliberate architectural choice, not an optimization added later.

## AI Extraction vs Deterministic Scoring

ArbiLens separates these concerns on purpose.

AI is used for:

- clause classification when heuristics are ambiguous
- concise explanation text for already-determined findings

Deterministic logic is used for:

- numeric risk scores
- severity assignment
- final scoring rubric behavior

Why that matters:

- the base score is stable and testable
- AI variability does not change the risk model
- the system stays explainable under review
- malformed AI outputs fail safely instead of silently becoming persisted findings

## Key Design Tradeoffs

- The auth model is intentionally simple JWT-based org-scoped auth rather than a full enterprise identity stack.
- PDF parsing focuses on digital text extraction and does not attempt heavy OCR by default.
- AI extraction is bounded chunk-by-chunk instead of sending entire contracts in one prompt.
- Risk scoring is rules-based, which improves consistency but limits nuanced policy interpretation.
- The frontend uses straightforward client-side session storage for the MVP instead of more complex session infrastructure.

For the reasoning behind those choices, see `docs/design-decisions.md`.

## Local Development

### Docker-first path

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
docker compose -f infra/docker-compose.yml up --build
```

The Compose stack runs migrations automatically through a one-shot `migrate` service before the API and worker start.

If you prefer a command wrapper:

```bash
make bootstrap
make up
```

Local endpoints:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`

### Backend without Docker

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload
```

Run the worker:

```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_worker.celery_app worker --loglevel=info
```

### Frontend without Docker

```bash
cd frontend
npm install
npm run dev
```

## Testing

Backend:

```bash
cd backend
source .venv/bin/activate
pytest app/tests
```

Frontend:

```bash
cd frontend
npm install
npm test
```

Browser-level e2e:

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

Useful backend test areas already covered:

- auth and protected routes
- upload validation
- parsing
- normalization
- clause extraction
- deterministic scoring
- AI schema validation and malformed-response handling
- API serialization contract validation
- reports
- comparisons
- workflow happy path and failure paths
- one browser-level login -> upload -> completed-results path with Playwright-backed API mocking

## Developer Setup

Configuration files:

- `backend/.env.example`
- `frontend/.env.example`

Important backend variables:

- `DATABASE_URL`
- `REDIS_URL`
- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `JWT_SECRET_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `APP_BASE_URL`

Additional setup notes: `docs/development.md`

Operational and deployment notes: `docs/deployment.md`

Reliability and failure-mode notes: `docs/reliability.md`

Productionization priorities: `docs/adr-productionization-next.md`

## API Notes

Authentication:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/users/me`

Document workflow:

- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{id}`
- `GET /api/v1/documents/{id}/status`
- `GET /api/v1/documents/{id}/summary`
- `GET /api/v1/documents/{id}/clauses`
- `GET /api/v1/documents/{id}/risks`

Additional product endpoints:

- reports under `/api/v1/reports`
- comparisons under `/api/v1/comparisons`
- billing under `/api/v1/billing`

The API contracts are typed on both the backend and frontend. The frontend consumes the backend through `frontend/lib/api/client.ts` and `frontend/lib/api/types.ts`.

## Security And Data-Handling Considerations

- The API is organization-scoped; document access is filtered by the authenticated user organization.
- Uploads are validated for extension, MIME type, emptiness, size, and basic file signature.
- Task errors are sanitized before being returned to clients.
- The AI layer avoids dumping raw contract text into plain logs.
- Risk findings and summaries are traceable to stored clause/risk records and citations.

This is still an MVP-level security posture. Notable gaps remain around browser session handling, secret management in real deployments, and deeper audit logging.

## Current Limitations

- No heavy OCR fallback for scanned PDFs
- No full enterprise auth model or SSO
- No browser-level frontend integration test suite
- Stripe webhook handling does not yet persist processed event IDs for idempotency
- Readiness checks are practical but not a full operational health system

## Future Improvements

- OCR fallback for image-only PDFs
- richer comparison explanations grounded in structured diffs
- stronger observability around queue depth, failures, and worker performance
- extend CI to include linting, dependency checks, and browser-level integration coverage
- more robust frontend auth/session handling
- webhook idempotency persistence and broader billing coverage

## Deployment

The repository includes deployment-oriented Dockerfiles and local Compose configuration, but it should not be described as production-ready without additional infrastructure and operational work.

Deployment notes:

- `docs/adr-productionization-next.md`
- `docs/architecture.md`
- `docs/design-decisions.md`
- `docs/deployment.md`
- `docs/development.md`
- `docs/reliability.md`
