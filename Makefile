.PHONY: install backend frontend dev test migrate help

help:
	@echo "Available commands:"
	@echo "  make install   - Install all dependencies"
	@echo "  make backend   - Run the backend server"
	@echo "  make frontend  - Run the frontend dev server"
	@echo "  make dev       - Run both backend and frontend"
	@echo "  make test      - Run backend tests"
	@echo "  make migrate   - Run database migrations"

install:
	cd backend && poetry install
	cd frontend && npm install

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

migrate:
	cd backend && poetry run alembic upgrade head
