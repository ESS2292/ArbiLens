.PHONY: bootstrap up down rebuild migrate backend worker frontend test-backend test-frontend

bootstrap:
	cp -n backend/.env.example backend/.env || true
	cp -n frontend/.env.example frontend/.env.local || true

up:
	docker compose -f infra/docker-compose.yml up --build

down:
	docker compose -f infra/docker-compose.yml down

rebuild:
	docker compose -f infra/docker-compose.yml down -v
	docker compose -f infra/docker-compose.yml up --build

migrate:
	docker compose -f infra/docker-compose.yml run --rm migrate

backend:
	cd backend && python3.12 -m venv .venv && . .venv/bin/activate && pip install -e .[dev] && alembic upgrade head && uvicorn app.main:app --reload

worker:
	cd backend && . .venv/bin/activate && celery -A app.workers.celery_worker.celery_app worker --loglevel=info

frontend:
	cd frontend && npm install && npm run dev

test-backend:
	cd backend && . .venv/bin/activate && pytest app/tests

test-frontend:
	cd frontend && npm test
