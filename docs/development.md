# Development Notes

## Local Stack

The default local workflow uses Docker Compose:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
docker compose -f infra/docker-compose.yml up --build
```

Equivalent shortcut:

```bash
make bootstrap
make up
```

What happens during `up`:

- Postgres, Redis, and MinIO start
- a one-shot `migrate` container runs `alembic upgrade head`
- the API starts after migrations complete
- the worker starts after migrations and object storage initialization complete
- the frontend starts after the API health check passes

Services exposed locally:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`

If you change models or Alembic revisions later, rerun migrations explicitly:

```bash
docker compose -f infra/docker-compose.yml run --rm migrate
```

Equivalent shortcut:

```bash
make migrate
```

## Running Components Separately

Backend API:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload
```

Worker:

```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_worker.celery_app worker --loglevel=info
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Recommended practical local workflow:

- use Docker Compose for Postgres, Redis, and MinIO
- run backend and worker locally when actively changing Python code
- run frontend locally when actively changing UI code

That gives faster edit/run cycles while keeping the dependent services reproducible.

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

The current e2e path covers:

- sign in
- dashboard load
- upload form flow
- navigation to document results
- completed summary, clause, and risk rendering

It uses Playwright with browser-level API mocking so the UI flow is exercised in a real browser without requiring a fully running backend stack.

## Useful Development Checks

Compile backend modules:

```bash
python3 -m compileall backend/app backend/alembic
```

## Environment Notes

The backend `.env.example` includes local-development defaults for:

- Postgres
- Redis
- MinIO
- OpenAI
- Stripe

Local development does not require live OpenAI or Stripe credentials unless you are exercising those specific paths.

For real development work, replace at minimum:

- `JWT_SECRET_KEY`
- `OPENAI_API_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`

## Workflow Notes

The main workflow to verify locally is:

1. register or log in
2. upload a valid PDF or DOCX contract
3. watch the document status move through queued, parsing, and analyzing
4. open the document detail page once completed
5. inspect summary, clauses, and risks
6. optionally generate a report or compare two completed contracts

## Startup Commands

Full stack with containers:

```bash
docker compose -f infra/docker-compose.yml up --build
```

Or:

```bash
make up
```

Stop the stack:

```bash
docker compose -f infra/docker-compose.yml down
```

Or:

```bash
make down
```

Rebuild from scratch:

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up --build
```

Or:

```bash
make rebuild
```
