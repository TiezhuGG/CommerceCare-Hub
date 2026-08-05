.PHONY: install format lint typecheck test migrate seed reset up down frontend-check

install:
	uv sync --all-groups

format:
	uv run ruff format backend/app backend/tests

lint:
	uv run ruff check backend/app backend/tests

typecheck:
	uv run mypy backend/app

test:
	uv run pytest

migrate:
	uv run alembic upgrade head

seed:
	uv run python scripts/seed.py

reset:
	uv run python scripts/reset.py

up:
	docker compose up --build

down:
	docker compose down

frontend-check:
	npm --prefix frontend run check
