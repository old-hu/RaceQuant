.PHONY: dev-backend dev-frontend test-backend lint-python lint-frontend lint format build-frontend smoke-frontend quality docker-up docker-down build-local-data rebuild-local-data audit-data diagnose-scrape train-when-ready

dev-backend:
	cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev -- --host 127.0.0.1

test-backend:
	PYTHONPATH=backend python -m pytest

lint-python:
	python -m compileall -q backend scripts

lint-frontend:
	cd frontend && npm run lint

lint: lint-python lint-frontend

format:
	cd frontend && npm run lint:fix

build-frontend:
	cd frontend && npm run build

smoke-frontend:
	cd frontend && npm run build
	cd frontend && npm run smoke

quality:
	python scripts/quality_check.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down

build-local-data:
	python scripts/build_local_data.py --source auto

rebuild-local-data:
	python scripts/build_local_data.py --source auto --reset

audit-data:
	python scripts/audit_data_readiness.py

diagnose-scrape:
	python scripts/diagnose_scrape_jobs.py

train-when-ready:
	python scripts/train_when_ready.py
