.DEFAULT_GOAL := help

.PHONY: help install dev test test-unit test-integration lint typecheck format dashboard build clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all Python packages and dashboard dependencies
	pip install -e "packages/flowforge-sdk[all]"
	pip install -e packages/flowforge-cli
	pip install -e server
	cd dashboard && pnpm install

dev: ## Start infrastructure (postgres + redis) via docker-compose
	docker-compose up -d

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only (no infrastructure required)
	pytest tests/unit

test-integration: ## Run integration tests (requires running postgres + redis)
	pytest tests/integration

lint: ## Run ruff linter
	ruff check .

typecheck: ## Run mypy type checker
	mypy packages/flowforge-sdk/src packages/flowforge-cli/src server/src

format: ## Auto-fix lint and format issues
	ruff format .
	ruff check --fix .

dashboard: ## Start the Next.js dashboard in development mode
	cd dashboard && pnpm dev

build: ## Build the Next.js dashboard for production
	cd dashboard && pnpm build

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
