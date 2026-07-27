.PHONY: help up down logs install install-frontend dev dev-frontend migrate upgrade downgrade history \
        test test-domain test-services test-api test-utils coverage lint format check clean

# Default target

help: ## Show all available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# Docker

up: ## Start PostgreSQL in the background
	cd docker && docker compose up -d

down: ## Stop all services
	cd docker && docker compose down

logs: ## Follow logs for all services
	cd docker && docker compose logs -f

# Python 

install: ## Install all Python dependencies including dev extras
	uv sync --all-extras

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

install-all: install install-frontend ## Install backend + frontend dependencies

# Development servers

dev: ## Run the FastAPI dev server locally (hot reload)
	uv run uvicorn src.main:app --reload --port 8000

dev-frontend: ## Run the Vite dev server (hot reload)
	cd frontend && npm run dev

# Database / Alembic

migrate: ## Generate a new migration  (usage: make migrate MSG="add users table")
	uv run alembic revision --autogenerate -m "$(MSG)"

upgrade: ## Apply all pending migrations
	uv run alembic upgrade head

downgrade: ## Roll back one migration
	uv run alembic downgrade -1

history: ## Show migration history
	uv run alembic history --verbose

# Tests

test: ## Run the full test suite
	uv run pytest -v

test-utils: ## Run pure-logic unit tests (no DB, no stubs)
	uv run pytest tests/test_utils/ -v

test-domain: ## Run DB behavior tests (fake SQLite)
	uv run pytest tests/test_domain/ -v

test-services: ## Run service-boundary tests (Groq stubbed)
	uv run pytest tests/test_services/ -v

test-api: ## Run HTTP endpoint tests
	uv run pytest tests/test_api/ -v

coverage: ## Run tests with coverage report
	uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Code quality 

lint: ## Run ruff linter + mypy type checker
	uv run ruff check . && uv run mypy src/

format: ## Auto-format code with ruff
	uv run ruff format .

check: ## Full quality gate: lint + format check + types (run before committing)
	uv run ruff check . \
		&& uv run ruff format --check . \
		&& uv run mypy src/

lint-frontend: ## Run eslint on the frontend
	cd frontend && npm run lint

# Cleanup 

clean: ## Remove caches, coverage artifacts, and __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage