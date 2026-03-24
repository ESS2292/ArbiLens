# Deployment Notes

This repository includes deployment-oriented Dockerfiles and a usable local Compose setup. It should still be described as deployment-ready development infrastructure, not as a production-hardened release template.

## Runtime Topology

Expected services:

- `frontend`: Next.js standalone app
- `backend`: FastAPI API server
- `worker`: Celery worker
- `postgres`
- `redis`
- `s3-compatible object storage`

The backend API and worker must share the same application configuration for database, Redis, object storage, OpenAI, and Stripe.

## Required Environment Variables

Backend:

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `JWT_SECRET_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `APP_BASE_URL`

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`

## Startup Order

1. Start Postgres, Redis, and object storage.
2. Ensure the object storage bucket exists.
3. Apply database migrations.
4. Start the backend API.
5. Start Celery workers.
6. Start the frontend.
7. Register the Stripe webhook endpoint if billing is enabled.

For this repository, the local Compose stack now encodes most of that flow directly:

- `minio-init` creates the bucket
- `migrate` runs `alembic upgrade head`
- `backend` and `worker` depend on successful migration completion

## Health Endpoints

- liveness: `GET /api/v1/health`
- readiness: `GET /api/v1/ready`

The current readiness implementation checks:

- database connectivity
- Redis reachability
- object storage bucket access

That is useful, but still not a full operations-grade readiness model.

Container health checks in this repo are intentionally basic:

- frontend: HTTP GET on `/`
- backend: HTTP GET on `/api/v1/health`
- minio: built-in live health endpoint

These checks are suitable for local reproducibility, not for full production operations.

## Deployment Considerations

### Backend

- run behind a reverse proxy or managed ingress
- keep the API stateless
- run Alembic migrations as a deployment step
- store secrets outside the repository

### Workers

- scale independently from the API
- monitor retries, stuck jobs, and failed jobs
- deploy worker and backend together to avoid schema drift

### Frontend

- build with `next build`
- run the standalone server
- point `NEXT_PUBLIC_API_BASE_URL` at the deployed backend origin

### Postgres

- use backups and point-in-time recovery
- size connections according to API and worker concurrency

### Redis

- isolate broker traffic from the public internet
- size memory and persistence for expected worker volume

### Object Storage

- use separate buckets or prefixes per environment
- restrict credentials to least privilege

## Stripe Notes

If billing is enabled, configure webhooks for:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Current implementation verifies webhook signatures, but does not yet persist processed event IDs for webhook-level idempotency.

## AI And Object Storage Notes

- OpenAI configuration is optional for basic local startup, but required for AI-assisted clause extraction and explanation paths.
- Stripe configuration is optional for basic local startup, but required for billing flows.
- Object storage is required even in local development because uploads and report exports are persisted through the storage abstraction.

## Known Operational Limitations

- Compose is suitable for local development, not full deployment orchestration.
- Frontend runtime configuration is minimal and intended for local/default use.
- CI exists for backend tests plus frontend typechecks and tests, but release automation is not included.
- No production secret-management, ingress, or managed service configuration is defined here.
- Worker observability is limited to logs and persisted job state.
- Readiness checks are practical, not exhaustive.

## What Still Prevents A Production Claim

- no release automation or deployment pipeline
- no infrastructure-as-code beyond local Docker Compose
- no advanced observability stack
- no webhook idempotency persistence
- no enterprise auth/session design
- no documented backup, restore, or incident-response process
