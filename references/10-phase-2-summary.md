# Phase 2 Summary

**Completed:** April 2026
**Status:** ✅ Production-ready

---

## What Was Built

Phase 2 added four major capability layers on top of the Phase 1 scaffold:
RAG-powered generation, spend controls, HubSpot CRM integration, and a complete execution UI with retry.

---

## 1. Voice Pack RAG

**Goal:** Generate content that actually sounds like your brand, not generic AI output.

**How it works:**
- When you ingest a canon document into a Voice Pack (`POST /api/voice-packs/{id}/ingest`), the API embeds it using the embeddings model and stores the 1536-dim vector in `canon_documents.embedding` (pgvector column).
- At generation time, the content generator embeds the generation intent (asset type + campaign goal + audience), runs a cosine similarity search (`<=>` operator) against all canon docs for that voice pack, and retrieves the top-5 closest examples.
- Those examples are injected into the system prompt as few-shot demonstrations before the model generates output.

**Files changed:**
- `apps/api/app/services/embeddings.py` — NEW. `embed_text()` and `embed_texts()` via OpenAI `text-embedding-3-small` (or pseudo-embed fallback if no key)
- `apps/api/app/services/rag.py` — NEW. `retrieve_canon_examples()` using pgvector cosine distance
- `apps/api/app/routers/content.py` — replaced naive full-table canon doc load with RAG retrieval call

---

## 2. Spend Controls

**Goal:** Automatically block campaign sends when the budget is exhausted.

**How it works:**
- `campaigns.budget` stores the total approved spend cap (NUMERIC 12,2)
- Before every execution run, the API sums all `analytics_events` where `event_type = 'spend'` for that campaign
- If `total_spend >= budget`, the run is rejected with HTTP 402 and a descriptive error message
- Budget is visible in the campaign detail page meta pills

**Files changed:**
- `apps/api/alembic/versions/0002_spend_controls.py` — NEW migration: `budget` on `campaigns`, `hubspot_list_id` on `campaign_channels`, `retried_from_id` on `execution_runs`
- `apps/api/app/routers/executions.py` — spend gate added to `run_execution`

**To set a budget:**
When creating or updating a campaign, include `"budget": 5000.00` in the payload.

---

## 3. HubSpot CRM Integration

**Goal:** Send emails to real contact lists from HubSpot rather than hardcoded test addresses.

**How it works:**
- Add `HUBSPOT_ACCESS_TOKEN=pat-...` to `.env`
- The integration page (`/integrations`) shows live connection status, portal domain, and can list all available contact lists with their sizes and IDs
- Campaign channels can carry a `config.hubspot_list_id` pointing at a HubSpot list
- At execution time, the API fetches email addresses from that list (paginated, up to 500 contacts) and passes them to SendGrid

**Files changed:**
- `apps/api/app/services/hubspot.py` — NEW. `get_lists()`, `get_list_emails()`, `get_contact_by_email()`, `verify_connection()`
- `apps/api/app/services/execution.py` — NEW `resolve_email_recipients()` (HubSpot list → fallback to test email)
- `apps/api/app/routers/executions.py` — fetches `CampaignChannel`, extracts `hubspot_list_id`, passes to `resolve_email_recipients()`
- `apps/api/app/routers/integrations.py` — NEW. `GET /api/integrations/status`, `GET /api/integrations/hubspot/lists`
- `apps/api/app/main.py` — registered integrations router

**HubSpot Setup:**
1. HubSpot → Settings → Integrations → Private Apps → Create
2. Scopes required: `crm.lists.read`, `crm.objects.contacts.read`
3. Copy token to `.env`: `HUBSPOT_ACCESS_TOKEN=pat-...`
4. Check `/integrations` page — should show "Connected" with portal info

**Targeting a list:**
When creating a campaign channel, set `config: { "hubspot_list_id": "123" }`. The list ID is visible in the `/integrations` page lists table.

---

## 4. Execution UI — Content Factory + Retry

**Goal:** Full submit → approve → execute flow in the UI, plus retry for failed sends.

**Campaign detail page (`/campaigns/[id]`) now includes:**

| Section | What it does |
|---|---|
| Meta pills | Audience, launch date, budget, channels — all at a glance |
| Compliance banner | Amber warning card if `compliance_notes` is set |
| Generate bar | Inline asset generation — type + variant count |
| **Content tab** | All assets for this campaign, grouped by asset type |
| Asset card | Status (draft / pending / approved / rejected), variant count, created date |
| Submit button | Appears on draft assets — submits for approval queue |
| Execute panel | Appears on approved assets — pick channel, provider, paste approval ID, hit Send |
| Variant viewer | Expand any asset to see all variants with full body content (subject, html_body, hashtags, etc.) |
| **Executions tab** | Table of all runs — status badge, channel, provider, provider message ID, timestamp |
| Retry button | Appears on failed runs — creates a new run with a fresh idempotency key |

**Files changed:**
- `apps/web/src/app/(dashboard)/campaigns/[id]/page.tsx` — full rewrite
- `apps/web/src/app/(dashboard)/integrations/page.tsx` — live status from API, HubSpot lists panel
- `apps/web/src/lib/api.ts` — added `content.listByCampaign`, `content.get`, `executions.*`, `integrations.*`

---

## 5. Moonshot AI (Kimi) — Default LLM Provider

The platform now ships with Moonshot AI (`moonshot-v1-8k`) as the default content generation model.

**Config:**
```
DEFAULT_MODEL_PROVIDER=moonshot
DEFAULT_EXTERNAL_MODEL=moonshot-v1-8k
MOONSHOT_API_KEY=sk-...
```

**How it's wired:**
- `apps/api/app/config.py` — added `moonshot_api_key`, `moonshot_base_url`, defaulted provider to `moonshot`
- `apps/api/app/services/content_generator.py` — added `_call_moonshot()` using the OpenAI SDK pointed at `https://api.moonshot.cn/v1`

**Provider priority:** `moonshot` → `anthropic` → `openai` (set via `DEFAULT_MODEL_PROVIDER` in `.env`)

See `references/05-llm-providers.md` for the full provider reference.

---

## Database Migrations

| Migration | Contents |
|---|---|
| `0001_initial` | All 16 base tables |
| `0002_spend_controls` | `campaigns.budget`, `campaign_channels.hubspot_list_id` (via config JSONB), `execution_runs.retried_from_id` |

Run all migrations: `make migrate`

---

## New API Endpoints (Phase 2)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/content/campaign/{campaign_id}` | All assets for a campaign (with variants) |
| `GET` | `/api/content/{asset_id}` | Single asset with all variants |
| `GET` | `/api/executions/campaign/{campaign_id}` | All execution runs for a campaign |
| `POST` | `/api/executions/{run_id}/retry` | Retry a failed execution run |
| `GET` | `/api/integrations/status` | Connection status for all providers |
| `GET` | `/api/integrations/hubspot/lists` | HubSpot contact lists |

---

## Environment Variables Added in Phase 2

```env
# Moonshot AI (Kimi)
MOONSHOT_API_KEY=sk-...
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
DEFAULT_MODEL_PROVIDER=moonshot
DEFAULT_EXTERNAL_MODEL=moonshot-v1-8k

# HubSpot CRM
HUBSPOT_ACCESS_TOKEN=pat-...
```
