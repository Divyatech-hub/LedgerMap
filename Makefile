SHELL := /bin/zsh

BACKEND_DIR := backend

.PHONY: install test lint format api db-up db-down db-migrate db-revision db-reset

install:
	cd $(BACKEND_DIR) && python -m pip install -e ".[dev]"

test:
	cd $(BACKEND_DIR) && python -m pytest

lint:
	cd $(BACKEND_DIR) && ruff check src tests

format:
	cd $(BACKEND_DIR) && ruff format src tests

api:
	cd $(BACKEND_DIR) && uvicorn ledgermap.main:app --reload

db-up:
	docker compose up -d postgres

db-down:
	docker compose stop postgres

db-migrate:
	cd $(BACKEND_DIR) && alembic upgrade head

db-revision:
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(m)"

db-reset:
	docker compose down -v
	docker compose up -d postgres
	$(MAKE) db-migrate