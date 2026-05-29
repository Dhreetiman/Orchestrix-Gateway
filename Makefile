.PHONY: help up down restart logs ps build migrate seed shell-api shell-db psql redis-cli test lint format typecheck web-dev web-build web-lint web-types clean

# Default target
help:
	@echo "Orchestrix Gateway — Make targets"
	@echo ""
	@echo "  make up          Start the stack (api, postgres, redis)"
	@echo "  make down        Stop the stack"
	@echo "  make restart     Restart the stack"
	@echo "  make logs        Tail logs from all services"
	@echo "  make ps          Show running services"
	@echo "  make build       Rebuild images"
	@echo ""
	@echo "  make migrate     Run alembic migrations against the running db"
	@echo "  make seed        Create an API key (prints raw key once)"
	@echo "  make shell-api   Open a shell inside the api container"
	@echo "  make psql        Open psql against the running postgres"
	@echo "  make redis-cli   Open redis-cli against the running redis"
	@echo ""
	@echo "  make test        Run backend tests"
	@echo "  make lint        Run ruff lint"
	@echo "  make format      Run ruff format"
	@echo "  make typecheck   Run mypy"
	@echo ""
	@echo "  make web-dev     Run the Next.js frontend in dev mode"
	@echo "  make web-build   Build the Next.js frontend"
	@echo "  make web-lint    Run ESLint on the frontend"
	@echo "  make web-types   Run tsc --noEmit on the frontend"
	@echo ""
	@echo "  make clean       Remove volumes (DESTRUCTIVE)"

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

build:
	docker compose build

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.scripts.create_api_key

shell-api:
	docker compose exec api /bin/bash

psql:
	docker compose exec postgres psql -U orchestrix -d orchestrix

redis-cli:
	docker compose exec redis redis-cli

test:
	cd backend && pytest

lint:
	cd backend && ruff check app tests

format:
	cd backend && ruff format app tests

typecheck:
	cd backend && mypy

web-dev:
	cd frontend && pnpm dev

web-build:
	cd frontend && pnpm build

web-lint:
	cd frontend && pnpm lint

web-types:
	cd frontend && pnpm typecheck

clean:
	docker compose down -v
