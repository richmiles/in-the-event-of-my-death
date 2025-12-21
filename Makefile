.PHONY: install backend frontend dev test migrate lint format format-check typecheck check hooks help

help:
	@echo "Available commands:"
	@echo "  make install   - Install all dependencies"
	@echo "  make backend   - Run the backend server"
	@echo "  make frontend  - Run the frontend dev server"
	@echo "  make dev       - Run both backend and frontend"
	@echo "  make test      - Run backend tests"
	@echo "  make lint      - Run lint checks"
	@echo "  make format    - Auto-format code"
	@echo "  make typecheck - Run TypeScript type checking"
	@echo "  make check     - Run lint, typecheck, and tests"
	@echo "  make hooks     - Install git hooks"
	@echo "  make migrate   - Run database migrations"

install:
	cd backend && poetry install
	cd frontend && npm install
	@make hooks

backend:
	cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend and frontend..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo ""
	@make -j2 backend frontend

test:
	cd backend && poetry run pytest tests/ -v

lint:
	cd backend && poetry run ruff check .
	cd frontend && npm run lint

format:
	cd backend && poetry run ruff format .
	cd frontend && npm run format:write

format-check:
	cd backend && poetry run ruff format --check .
	cd frontend && npm run format

typecheck:
	# Use project references so the app config is actually typechecked
	cd frontend && npx tsc -b

check: lint format-check typecheck test

hooks:
	git config core.hooksPath .githooks

migrate:
	cd backend && poetry run alembic upgrade head
