# Database Schema

All tables use UUID primary keys. Business tables include `tenant_id`, `created_at`, `updated_at`, `created_by`.

## Tables

### `tenants`
Workspace isolation unit. All data is scoped to a tenant.

### `users` + `roles` + `user_roles`
Users belong to a tenant. Roles are also tenant-scoped. Many-to-many via `user_roles`.

Built-in role names: `workspace_admin`, `marketing_lead`, `content_operator`, `approver`, `analyst`

### `campaigns`
Top-level object. Status machine:
```
draft → pending_approval → approved → executing → live → paused/complete/archived
```

### `campaign_channels`
One row per channel per campaign. Channels: `email` | `social` | `landing_page` | `ad` | `sms`

### `voice_packs`
Versioned brand voice configuration. Contains tone settings, vocabulary, banned phrases, claims policy, style summary (used as AI system prompt prefix).

### `canon_documents`
Sample content used for few-shot retrieval. Stores raw content + 1536-dim vector embedding (pgvector).

### `content_assets`
One per generated asset type/channel combo within a campaign.

Status: `draft` → `review` → `approved` → `published` → `archived`

### `content_variants`
Multiple variants per asset (A/B). Stores body as JSONB (flexible per channel type):
- Email: `{ subject, preheader, html_body, text_body }`
- Social: `{ caption, hashtags, image_prompt }`
- Landing page: `{ headline, subheadline, cta, sections }`
- Ad copy: `{ headline, description, cta }`

Tracks `model_used`, `prompt_hash`, `banned_phrase_flags`, `claim_warnings`, `quality_score`.

### `approvals` + `approval_comments`
First-class approval records. Types: `content` | `publish` | `spend` | `outbound`

Status: `pending` → `approved` | `rejected` | `changes_requested`

Stores `policy_check_results` (brand/pii/claims pass/fail).

### `execution_runs`
Receipt for every execution attempt. Has `idempotency_key` (SHA-256 of campaign+asset+channel) to prevent duplicate sends. Status: `queued` → `running` → `success` | `failed` | `retrying`

### `analytics_events`
High-volume event log. Event types: `send` | `open` | `click` | `conversion` | `spend` | `impression` | `bounce`

### `audit_logs`
**Append-only.** Never updated. Every mutation to any business object writes a row here. Used for compliance reporting and SIEM export.

## Key Design Decisions

- **JSONB for asset bodies** — allows email/social/landing/ad structures to evolve without schema migrations
- **Vector(1536) on canon_documents** — for semantic retrieval of brand examples at generation time
- **Idempotency keys on execution_runs** — prevents duplicate sends if the API is called twice
- **Voice packs are versioned** — bumps `version` on every substantive update, never mutates in place
- **Audit log is append-only** — no UPDATE or DELETE ever runs against it
