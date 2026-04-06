# Phase 3 Summary

**Completed:** April 2026
**Status:** ✅ Production-ready

---

## What Was Built

Phase 3 added two major systems: an **Experiment Engine** for A/B testing content variants with statistical significance, and an **MCP Gateway** — a unified connector dispatch layer that routes campaign executions through real provider APIs.

---

## 1. Experiment Engine (A/B Testing)

**Goal:** Statistically determine which content variant performs best and automatically promote the winner.

**How it works:**
- Create an experiment for any asset that has 2+ variants (`POST /api/experiments`)
- Assign traffic weights to control the split — e.g. 50/50, 80/20 (`POST /api/experiments/{id}/set-weights`)
- Call `select-variant` before each send to get a weighted-random variant assignment
- Record `impression`, `click`, and `conversion` events per variant (`POST /api/experiments/{id}/record-event`)
- The service runs a **two-proportion z-test** (standard library math, no external deps) after every conversion event
- When any treatment variant reaches the configured confidence threshold (default 95%) with ≥30 impressions, the experiment auto-concludes and promotes the winner to `is_active=true`
- Minimum sample size guard: 30 impressions per variant before auto-conclude fires

**Statistical confidence examples:**
| Scenario | Confidence |
|---|---|
| n=50, 10% vs 14% CVR | 46% — keep running |
| n=200, 10% vs 14% CVR | 78% — getting there |
| n=1,000, 10% vs 14% CVR | 99.4% — auto-conclude |
| n=500, 5% vs 10% CVR | 99.7% — auto-conclude |

**Files:**
- `apps/api/alembic/versions/0003_experiment_engine.py` — `experiments` table, `traffic_weight` on `content_variants`, `variant_id` FK on `analytics_events`
- `apps/api/app/models/experiment.py` — `Experiment` model
- `apps/api/app/services/experiment.py` — weighted selection, z-test, stats computation
- `apps/api/app/schemas/experiment.py` — `ExperimentCreate`, `ExperimentDetailRead`, `VariantStats`
- `apps/api/app/routers/experiments.py` — 8 endpoints

**API Endpoints:**
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/experiments` | Create experiment for an asset |
| `GET` | `/api/experiments/campaign/{id}` | List experiments for a campaign |
| `GET` | `/api/experiments/{id}` | Live stats + significance per variant |
| `PATCH` | `/api/experiments/{id}` | Update name, hypothesis, pause/resume |
| `POST` | `/api/experiments/{id}/set-weights` | Adjust traffic split |
| `POST` | `/api/experiments/{id}/select-variant` | Weighted random variant selection |
| `POST` | `/api/experiments/{id}/record-event` | Track impression/click/conversion |
| `POST` | `/api/experiments/{id}/conclude` | Declare winner + promote |

**Frontend (Campaign detail → Experiments tab):**
- New Experiment form — pick asset, enter name
- A/B Test button on Content tab for assets with 2+ variants
- Live stats table — impressions, clicks, CTR, conversions, CVR, confidence
- Recharts bar chart — CVR per variant (green = winner, violet = leading)
- Confidence badges — grey → yellow → green as significance builds
- Declare Winner button → promotes to active, deactivates others
- Pause / Resume toggle

---

## 2. MCP Gateway

**Goal:** Route every campaign execution through a single unified dispatch layer with real provider APIs — no provider logic in routers.

**Architecture:**

```
Router → gateway.dispatch() → ConnectorAdapter.publish() → ConnectorJob record → ExecutionRun update
```

Every execution creates a `ConnectorJob` row for full traceability, independent of the `ExecutionRun`.

**Connector Adapters (all implement `validate()` + `publish()`):**

| Provider | Channel | What it does |
|---|---|---|
| `sendgrid` | email | Sends via SendGrid v3 `/mail/send` |
| `klaviyo` | email / sms | Creates Klaviyo campaign → schedules send → polls status |
| `meta_ads` | social / ad | Creates ad creative + ad (starts PAUSED for safety) |
| `google_ads` | ad | Creates RSA via Ads API v17 with inline OAuth token refresh |
| `webflow` | landing_page | Creates CMS item + publishes site |

**Credential storage:**
- Credentials stored per-tenant per-provider in `connector_credentials` table (JSONB)
- Values are never returned by the API — only key names are shown
- In production: encrypt the JSONB blob at rest via Vault or AWS KMS (Phase 4)
- Fallback: env-level keys (`SENDGRID_API_KEY`, `HUBSPOT_ACCESS_TOKEN`) still work for Phase 1/2 providers

**Files:**
- `apps/api/alembic/versions/0004_mcp_gateway.py` — `connector_credentials`, `connector_jobs` tables
- `apps/api/app/models/connector.py` — `ConnectorCredential`, `ConnectorJob`
- `apps/api/app/services/connectors/base.py` — `ConnectorAdapter` ABC, payload/result dataclasses
- `apps/api/app/services/connectors/sendgrid.py`
- `apps/api/app/services/connectors/klaviyo.py`
- `apps/api/app/services/connectors/meta.py`
- `apps/api/app/services/connectors/google_ads.py`
- `apps/api/app/services/connectors/webflow.py`
- `apps/api/app/services/gateway.py` — registry, dispatch, credential resolution, validate_all
- `apps/api/app/schemas/connector.py`
- `apps/api/app/routers/connectors.py` — 7 endpoints
- `apps/api/app/routers/executions.py` — replaced all provider if/else with `gateway.dispatch()`

**API Endpoints:**
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/connectors/credentials` | Store/update credentials for a provider |
| `GET` | `/api/connectors/credentials` | List configured providers (keys only, no values) |
| `DELETE` | `/api/connectors/credentials/{id}` | Deactivate credentials |
| `POST` | `/api/connectors/credentials/{id}/verify` | Live test against provider API |
| `GET` | `/api/connectors/jobs` | All dispatch jobs (filter by campaign/provider) |
| `GET` | `/api/connectors/jobs/{id}` | Single job detail |
| `GET` | `/api/connectors/status` | Live health check across all 5 connectors |

**Frontend (Integrations page):**
- Live connector health cards for all 5 providers
- Inline credential form per provider (fields vary, secrets masked)
- Verify button — hits live provider API and shows result
- Remove button — deactivates stored credentials
- Shows which credential keys are stored (values never displayed)

**Adding a new connector (3 steps):**
1. Create `apps/api/app/services/connectors/yourprovider.py` implementing `ConnectorAdapter`
2. Add it to `_REGISTRY` in `apps/api/app/services/gateway.py`
3. Add its `credentialFields` to `PROVIDER_META` in the integrations page

---

## Database Migrations

| Migration | Contents |
|---|---|
| `0001_initial` | All 16 base tables |
| `0002_spend_controls` | `campaigns.budget`, `campaign_channels` config, `execution_runs.retried_from_id` |
| `0003_experiment_engine` | `experiments`, `content_variants.traffic_weight`, `analytics_events.variant_id` |
| `0004_mcp_gateway` | `connector_credentials`, `connector_jobs` |

---

## Total Route Count After Phase 3

**46 API routes** across 10 routers:
`auth`, `campaigns`, `content`, `approvals`, `voice`, `executions`, `analytics`, `audit`, `integrations`, `experiments`, `connectors`
