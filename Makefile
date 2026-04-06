.PHONY: up down migrate migrate-down api web install setup

PYTHON  = apps/api/.venv/bin/python
UV      = uv
PNPM    = pnpm

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker compose up -d db redis minio

down:
	docker compose down

up-all:
	docker compose up -d

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	cd apps/api && .venv/bin/alembic upgrade head

migrate-down:
	cd apps/api && .venv/bin/alembic downgrade -1

# ── Dev servers ───────────────────────────────────────────────────────────────
api:
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd apps/web && $(PNPM) dev

# ── Install ───────────────────────────────────────────────────────────────────
install:
	$(PNPM) install
	cd apps/api && $(UV) venv .venv && $(UV) pip install --python .venv/bin/python -e .

# ── Setup (first run) ─────────────────────────────────────────────────────────
setup: up
	@echo "Waiting for Postgres to be ready..."
	@sleep 5
	$(MAKE) migrate
	@echo ""
	@echo "Platform ready."
	@echo "  Run 'make api' to start the API  -> http://localhost:8000/docs"
	@echo "  Run 'make web' to start the UI   -> http://localhost:3000"
