.PHONY: dev dev-backend dev-frontend test backend-test frontend-test lint frontend-build build docker-up docker-down

dev: dev-backend

dev-backend:
	python backend/run.py

dev-frontend:
	cd frontend && npm run dev

test: backend-test frontend-test

backend-test:
	cd backend && python -m pytest --cov=app --cov-report=term-missing

frontend-test:
	cd frontend && npm test

frontend-build:
	cd frontend && npm run build

build: frontend-build

lint: frontend-build
	ruff check backend/app backend/tests

docker-up:
	docker compose up --build

docker-down:
	docker compose down
