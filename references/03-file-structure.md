# File Structure

```
executionmarketingplatform/
├── Makefile                        # Dev shortcuts (make setup, make api, make web)
├── docker-compose.yml              # Local infra: Postgres, Redis, MinIO, API, Web
├── .env.example                    # Copy to .env and fill in secrets
├── package.json                    # pnpm workspace root
├── pnpm-workspace.yaml
├── references/                     # This folder — notes and documentation
│
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── pyproject.toml          # Python dependencies (uv-compatible)
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       └── 0001_initial_schema.py   # Full DB schema migration
│   │   └── app/
│   │       ├── main.py             # FastAPI app, middleware, router registration
│   │       ├── config.py           # Settings from .env via pydantic-settings
│   │       ├── database.py         # Async SQLAlchemy engine + session dependency
│   │       ├── models/             # SQLAlchemy ORM models
│   │       │   ├── base.py         # TenantScopedBase (id, tenant_id, timestamps)
│   │       │   ├── tenant.py
│   │       │   ├── user.py         # User, Role, UserRole
│   │       │   ├── campaign.py     # Campaign, CampaignChannel
│   │       │   ├── content.py      # ContentAsset, ContentVariant
│   │       │   ├── voice.py        # VoicePack, CanonDocument (+ vector embedding)
│   │       │   ├── approval.py     # Approval, ApprovalComment
│   │       │   ├── execution.py    # ExecutionRun
│   │       │   ├── analytics.py    # AnalyticsEvent
│   │       │   └── audit.py        # AuditLog (append-only)
│   │       ├── schemas/            # Pydantic v2 request/response schemas
│   │       │   ├── campaign.py
│   │       │   ├── content.py
│   │       │   ├── voice.py
│   │       │   ├── approval.py
│   │       │   ├── execution.py
│   │       │   ├── analytics.py
│   │       │   ├── auth.py
│   │       │   └── audit.py
│   │       ├── routers/            # FastAPI route handlers
│   │       │   ├── deps.py         # Shared deps: get_current_user, require_roles, DB
│   │       │   ├── auth.py         # POST /api/auth/token
│   │       │   ├── campaigns.py    # CRUD + status transitions
│   │       │   ├── content.py      # Generate, rewrite, submit
│   │       │   ├── approvals.py    # Queue, decision, comments
│   │       │   ├── voice.py        # Voice packs, document ingestion
│   │       │   ├── executions.py   # Run approved campaigns
│   │       │   ├── analytics.py    # Event ingest + summary
│   │       │   └── audit.py        # Audit log viewer
│   │       └── services/
│   │           ├── auth.py         # JWT encode/decode, password hashing
│   │           ├── audit.py        # log_action() helper
│   │           ├── policy.py       # Banned phrase, PII, claims checks
│   │           ├── content_generator.py  # AI generation (Anthropic/OpenAI)
│   │           └── execution.py    # SendGrid send, social publish stubs
│
│   └── web/                        # Next.js 15 frontend
│       ├── package.json
│       ├── next.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── app/
│           │   ├── layout.tsx          # Root layout (fonts, providers, toaster)
│           │   ├── globals.css         # Tailwind + CSS vars + .input component
│           │   ├── login/page.tsx      # Login form (email + password + tenant_slug)
│           │   └── (dashboard)/        # Protected layout group
│           │       ├── layout.tsx      # Sidebar + main content wrapper
│           │       ├── page.tsx        # Home: KPIs, recent campaigns, pending approvals
│           │       ├── campaigns/
│           │       │   ├── page.tsx        # Campaign list with status filter
│           │       │   ├── new/page.tsx    # New campaign form
│           │       │   └── [id]/page.tsx   # Campaign detail + generate content
│           │       ├── content/page.tsx    # Content factory (campaign selector)
│           │       ├── approvals/page.tsx  # Approval queue with inline decisions
│           │       ├── voice/page.tsx      # Voice packs + ingest
│           │       ├── analytics/page.tsx  # KPI cards + channel bar chart
│           │       ├── integrations/page.tsx  # Integration status cards
│           │       └── admin/page.tsx      # Audit log viewer
│           ├── components/
│           │   ├── sidebar.tsx         # Navigation sidebar
│           │   └── providers.tsx       # TanStack Query provider
│           └── lib/
│               ├── api.ts             # Typed API client (axios + auth interceptors)
│               └── utils.ts           # cn(), formatDate(), formatDateTime(), pct()
```
