.PHONY: dev-backend dev-frontend test-backend lint-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && corepack pnpm dev

test-backend:
	cd backend && pytest

lint-frontend:
	cd frontend && corepack pnpm lint
