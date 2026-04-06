# Tech Stack

## Frontend — `apps/web`

| Tool | Purpose |
|---|---|
| Next.js 15 | React framework, App Router |
| TypeScript | Type safety |
| Tailwind CSS | Utility-first styling |
| shadcn/ui (planned) | Component library built on Radix UI |
| TanStack Query | Server state, caching, mutations |
| Axios | HTTP client with auth interceptors |
| Recharts | Analytics charts |
| Sonner | Toast notifications |
| Zod | Schema validation |

## Backend — `apps/api`

| Tool | Purpose |
|---|---|
| FastAPI | Python async web framework |
| SQLAlchemy 2 (async) | ORM with async sessions |
| Alembic | Database migrations |
| Pydantic v2 | Request/response validation |
| passlib + python-jose | Password hashing and JWT auth |
| asyncpg | Async Postgres driver |
| pgvector | Vector embeddings in Postgres |
| Anthropic SDK | Claude API for content generation |
| OpenAI SDK | GPT-4o fallback |
| httpx | Async HTTP for SendGrid + integrations |
| structlog | Structured logging |

## Infrastructure (Docker Compose — local dev)

| Service | Image | Port | Purpose |
|---|---|---|---|
| db | pgvector/pgvector:pg16 | 5432 | Postgres + vector extension |
| redis | redis:7-alpine | 6379 | Caching, session state |
| minio | minio/minio | 9000/9001 | Object storage (S3-compatible) |
| api | local build | 8000 | FastAPI backend |
| web | local build | 3000 | Next.js frontend |

## Production Stack (planned)

| Layer | Tech |
|---|---|
| Infra | Kubernetes + ArgoCD + Terraform |
| Auth | Keycloak (SSO/SAML/OIDC) + OpenFGA (permissions) |
| Policy | Open Policy Agent (OPA) |
| Secrets | HashiCorp Vault + KMS |
| Workflows | Temporal |
| Messaging | NATS JetStream / Kafka |
| Observability | OpenTelemetry + Prometheus + Grafana + Loki |
| Edge | Cloudflare / Fastly (WAF, DDoS) |
| Service mesh | Linkerd / Istio (mTLS) |
