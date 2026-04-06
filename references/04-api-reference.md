# API Reference

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs` (Swagger UI)

All endpoints except `/api/auth/token` and `/health` require:
```
Authorization: Bearer <jwt_token>
```

All business endpoints are tenant-scoped — the tenant is resolved from the JWT, not the URL.

---

## Auth

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/token` | Login — returns JWT |

**Login body:**
```json
{
  "email": "user@company.com",
  "password": "secret",
  "tenant_slug": "my-company"
}
```

---

## Campaigns

| Method | Path | Description |
|---|---|---|
| POST | `/api/campaigns` | Create campaign |
| GET | `/api/campaigns` | List campaigns (`?status=draft&page=1&page_size=20`) |
| GET | `/api/campaigns/{id}` | Campaign detail with channels |
| PATCH | `/api/campaigns/{id}` | Update campaign basics or status |

**Create body:**
```json
{
  "name": "Summer Sale",
  "goal": "Drive 500 sign-ups",
  "audience_summary": "SMB founders, US market",
  "channels": ["email", "social"],
  "offer": { "headline": "Start free", "cta": "Get started" },
  "brief": "Urgent but friendly tone.",
  "launch_at": "2026-05-01"
}
```

---

## Content

| Method | Path | Description |
|---|---|---|
| POST | `/api/content/generate` | Generate asset variants via AI |
| POST | `/api/content/{id}/rewrite` | Rewrite with a new instruction |
| POST | `/api/content/{id}/submit` | Submit for approval |

**Generate body:**
```json
{
  "campaign_id": "uuid",
  "asset_type": "email",
  "variant_count": 2,
  "voice_pack_id": "uuid (optional)"
}
```

Asset types: `email` | `social_post` | `landing_page` | `ad_copy`

---

## Approvals

| Method | Path | Description |
|---|---|---|
| POST | `/api/approvals` | Create approval request |
| GET | `/api/approvals` | List queue (`?status=pending`) |
| POST | `/api/approvals/{id}/decision` | Approve, reject, or request changes |
| POST | `/api/approvals/{id}/comments` | Add comment |

**Decision body:**
```json
{
  "decision": "approved",
  "comment": "Looks good, ship it."
}
```

Decisions: `approved` | `rejected` | `changes_requested`

---

## Voice Packs

| Method | Path | Description |
|---|---|---|
| GET | `/api/voice-packs` | List voice packs |
| POST | `/api/voice-packs` | Create voice pack |
| PATCH | `/api/voice-packs/{id}` | Update voice pack (bumps version) |
| POST | `/api/voice-packs/{id}/ingest` | Ingest URL or content as canon document |

---

## Executions

| Method | Path | Description |
|---|---|---|
| POST | `/api/executions/run` | Execute an approved campaign asset |

Requires a valid `approval_id` with `status = "approved"`. Uses idempotency key — safe to retry.

---

## Analytics

| Method | Path | Description |
|---|---|---|
| POST | `/api/analytics/events` | Ingest a tracking event |
| GET | `/api/analytics/summary` | KPI summary (`?campaign_id=uuid`) |

Event types: `send` | `open` | `click` | `conversion` | `spend` | `impression` | `bounce`

---

## Audit Log

| Method | Path | Description |
|---|---|---|
| GET | `/api/audit-logs` | Append-only log (`?action=campaign.created&page=1`) |

Requires `workspace_admin` or `analyst` role.
