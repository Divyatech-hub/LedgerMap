SHELL := /bin/zsh

BACKEND_DIR := backend
VENV_BIN := $(BACKEND_DIR)/.venv/bin

.PHONY: install test db-test-setup lint format api db-up db-down db-migrate db-revision db-reset

install:
	python3 -m venv $(BACKEND_DIR)/.venv
	$(VENV_BIN)/pip install -e "$(BACKEND_DIR)[dev]"

TEST_DATABASE_URL := postgresql+asyncpg://ledgermap:ledgermap@localhost:5432/ledgermap_test

test: db-test-setup
	cd $(BACKEND_DIR) && ../$(VENV_BIN)/python -m pytest

# Tests run against their own database so they never delete development data.
db-test-setup:
	docker compose exec -T postgres psql -U ledgermap -d ledgermap -tc \
		"SELECT 1 FROM pg_database WHERE datname = 'ledgermap_test'" | grep -q 1 || \
		docker compose exec -T postgres createdb -U ledgermap ledgermap_test
	cd $(BACKEND_DIR) && DATABASE_URL=$(TEST_DATABASE_URL) ../$(VENV_BIN)/alembic upgrade head

lint:
	cd $(BACKEND_DIR) && ../$(VENV_BIN)/ruff check src tests

format:
	cd $(BACKEND_DIR) && ../$(VENV_BIN)/ruff format src tests

api:
	cd $(BACKEND_DIR) && ../$(VENV_BIN)/uvicorn ledgermap.main:app --reload

db-up:
	docker compose up -d postgres

db-down:
	docker compose stop postgres

db-migrate:
	cd $(BACKEND_DIR) && ../$(VENV_BIN)/alembic upgrade head

db-revision:
	cd $(BACKEND_DIR) && ../$(VENV_BIN)/alembic revision --autogenerate -m "$(m)"

db-reset:
	docker compose down -v
	docker compose up -d postgres
	$(MAKE) db-migrate
