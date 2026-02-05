# Makefile for OC7-RAG Project
# Provides convenient shortcuts for common development tasks

.PHONY: help install test test-fast test-api test-coverage run verify docker-build docker-up docker-down docker-logs clean format lint

# Default target - show help
help:  ## Show this help message
	@echo "OC7-RAG Development Commands"
	@echo "============================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Setup and installation
install:  ## Install Python dependencies
	pip install -r requirements.txt

verify:  ## Verify setup is correct
	python scripts/verify_setup.py

# Testing
test:  ## Run all tests
	pytest tests/ -v

test-fast:  ## Run fast tests only (no integration tests)
	pytest tests/ -v -m "not integration"

test-api:  ## Test API endpoints (server must be running)
	bash scripts/test_api.sh

test-coverage:  ## Run tests with coverage report
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# Running the application
run:  ## Run API server locally
	python scripts/run_api.py

# Docker commands
docker-build:  ## Build Docker image
	docker build -t oc7-rag-api .

docker-up:  ## Start Docker containers (detached)
	docker-compose up -d

docker-down:  ## Stop Docker containers
	docker-compose down

docker-logs:  ## View Docker logs (follow mode)
	docker-compose logs -f

docker-restart:  ## Restart Docker containers
	docker-compose restart

docker-shell:  ## Open shell in running container
	docker-compose exec api /bin/bash

# Maintenance and cleanup
clean:  ## Clean build artifacts and cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true

format:  ## Format code with black (if installed)
	@command -v black >/dev/null 2>&1 && black src/ tests/ || echo "black not installed, skipping"

lint:  ## Run linting checks (if installed)
	@command -v flake8 >/dev/null 2>&1 && flake8 src/ tests/ || echo "flake8 not installed, skipping"
	@command -v pylint >/dev/null 2>&1 && pylint src/ || echo "pylint not installed, skipping"

# Development helpers
notebook:  ## Start Jupyter notebook server
	jupyter notebook notebooks/

check: verify test-fast  ## Quick check: verify setup + run fast tests

# Release helpers
version:  ## Show current version
	@grep -E "version.*=" src/api/main.py | head -1 || echo "Version not found"

# Production deployment (requires SSH access)
deploy-check:  ## Check production deployment status
	@echo "Checking production deployment..."
	@bash scripts/test_api.sh http://188.34.205.146:8000 || echo "Production API not responding"

# All-in-one targets
setup: install verify  ## Complete setup: install + verify

test-all: test test-api  ## Run all tests including API tests (requires running server)

dev: verify run  ## Development mode: verify + run API

# Docker all-in-one
docker-fresh: docker-down docker-build docker-up docker-logs  ## Fresh Docker deployment: down, build, up, logs
