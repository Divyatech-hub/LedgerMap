SHELL := /bin/zsh

BACKEND_DIR := backend
VENV_BIN := $(BACKEND_DIR)/.venv/bin

.PHONY: install test lint format api db-up db-down db-migrate db-revision db-reset

install:
	python3 -m venv $(BACKEND_DIR)/.venv
	$(VENV_BIN)/pip install -e "$(BACKEND_DIR)[dev]"

test:
	cd $(BACKEND_DIR) && ../$(VENV_BIN)/python -m pytest

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
