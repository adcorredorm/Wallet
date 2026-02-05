.PHONY: help install dev run init-db seed reset-db migrate upgrade downgrade routes clean test

help:
	@echo "Wallet Backend - Available Commands"
	@echo ""
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Run development server"
	@echo "  make init-db     - Initialize database with migrations and seed data"
	@echo "  make seed        - Seed database with predefined categories"
	@echo "  make reset-db    - Reset database (WARNING: Deletes all data)"
	@echo "  make migrate MSG='message' - Create new migration"
	@echo "  make upgrade     - Apply pending migrations"
	@echo "  make downgrade   - Revert last migration"
	@echo "  make routes      - List all API routes"
	@echo "  make clean       - Remove Python cache files"
	@echo "  make test        - Run tests (not implemented yet)"
	@echo ""

install:
	pip install -r requirements.txt

dev:
	python cli.py run

run: dev

init-db:
	python cli.py init-db

seed:
	python cli.py seed

reset-db:
	python cli.py reset-db

migrate:
	python cli.py migrate "$(MSG)"

upgrade:
	python cli.py upgrade

downgrade:
	python cli.py downgrade

routes:
	python cli.py routes

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

test:
	@echo "Tests not implemented yet"
	# pytest tests/
