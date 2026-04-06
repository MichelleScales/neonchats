# Getting Started

## Prerequisites

- Docker Desktop running
- Node.js 20+ and pnpm (`npm install -g pnpm`)
- Python 3.12+
- `uv` (`pip install uv`) — fast Python package manager
- macOS `make` (built-in) — **this is the Unix build tool, not make.com**

## First-Time Setup

```bash
# 1. Clone / open the project
cd executionmarketingplatform

# 2. Copy env file and fill in your API key
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Install all dependencies + start infra + run migrations
make setup

# 4. Start the API (in one terminal)
make api
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI — all endpoints)

# 5. Start the web app (in another terminal)
make web
# → http://localhost:3000
```

## Makefile Commands

| Command | What it does |
|---|---|
| `make setup` | install + start Docker + migrate DB |
| `make up` | start Postgres, Redis, MinIO (Docker) |
| `make down` | stop all Docker containers |
| `make migrate` | run Alembic migrations |
| `make migrate-down` | rollback one migration |
| `make api` | start FastAPI dev server (hot reload) |
| `make web` | start Next.js dev server (hot reload) |

**Note:** `make` here is the standard Unix/macOS build tool — it just runs shell commands. It has nothing to do with make.com (the workflow automation SaaS).

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (or OpenAI) | Claude API key from console.anthropic.com |
| `OPENAI_API_KEY` | Optional | GPT-4o fallback |
| `DEFAULT_MODEL_PROVIDER` | No | `anthropic` (default) or `openai` |
| `SECRET_KEY` | Yes (prod) | Long random string for JWT signing |
| `SENDGRID_API_KEY` | For email sends | From app.sendgrid.com |
| `DATABASE_URL` | Auto in Docker | asyncpg connection string |
| `REDIS_URL` | Auto in Docker | Redis connection string |

## Creating Your First Tenant + User

The database starts empty. Seed via the API or psql:

```sql
-- Connect: psql postgresql://emp:emp@localhost:5432/emp

INSERT INTO tenants (id, name, slug, plan)
VALUES (gen_random_uuid(), 'Acme Corp', 'acme', 'starter');

-- Get the tenant ID from above, then:
INSERT INTO users (id, tenant_id, email, full_name, hashed_password)
VALUES (
  gen_random_uuid(),
  '<tenant_id>',
  'admin@acme.com',
  'Admin User',
  -- bcrypt hash of 'password123' — generate with: python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('password123'))"
  '$2b$12$...'
);
```

Or add a `make seed` target in Phase 2 with a proper seed script.

## Switching LLM Provider

See `references/05-llm-providers.md` for full instructions on adding Moonshot AI or any OpenAI-compatible provider.
