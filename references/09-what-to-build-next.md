# What to Build Next

## Phase 1 — ✅ Complete
Core scaffold: campaigns, content, approvals, voice packs, analytics, audit log, auth.

## Phase 2 — ✅ Complete
RAG generation, spend controls, HubSpot CRM, execution UI with retry, Moonshot AI provider.
See `references/10-phase-2-summary.md` for full details.

---

## Phase 3 Priorities

### 1. Experiment Engine (A/B Testing)
- A/B variant selection on `content_variants` — flag each variant with a traffic weight
- Traffic allocation logic in `campaign_channels.config`
- Impression / click / conversion event tracking in `analytics_events`
- Statistical significance computation (chi-squared or Bayesian)
- Winner auto-promotion: promote winning variant to `is_active = true` when significance threshold reached
- UI: variant performance comparison chart on the campaign detail page

### 2. MCP Gateway + External Connectors
- Temporal or Celery for long-running campaign execution pipelines
- MCP connectors (one per channel) to replace stub `publish_social_post()`:
  - Google Ads — campaign creation, budget management
  - Meta Ads — ad set + creative upload
  - TikTok Ads — video creative delivery
  - Webflow — publish landing page variants
  - Klaviyo — email/SMS flows
  - Shopify — product feed enrichment for ad copy
- Connector auth: OAuth 2.0 token store per tenant in `integrations` table
- Quota tracking and rate-limit handling per connector

### 3. Private Model Plane
- vLLM or SGLang running open-weight models (Llama 3.1, Mistral) inside a VPC or local container
- Route PHI-tagged content to private plane automatically via data classification middleware
- Add `DEFAULT_MODEL_PROVIDER=private` branch in `content_generator.py`
- Per-tenant model selection (enterprise tenants → private; SMB → Moonshot/OpenAI)

### 4. OPA Policy Authoring UI
- Visual rule builder in the Admin section for brand compliance rules
- OPA bundle compiler — output Rego policies from the UI
- Policy evaluation middleware that checks generated content before it can be submitted for approval
- Webhook-based policy enforcement at gateway level for real-time decisioning

### 5. Advanced Approvals + Multi-Step Workflows
- Configurable approval chains (sequential: legal → brand → exec; parallel: any 2 of 3)
- SLA timers — auto-escalate if not reviewed within N hours
- Diff view in the approval drawer — show exactly what changed between variant versions
- External approver link (no login required — just approve/reject via signed URL)

### 6. Analytics Dashboard Improvements
- Spend vs. budget gauge chart per campaign
- Channel performance breakdown (email open rate, CTR, social engagement)
- Export to CSV / PDF
- Date range picker and campaign filter
- PostHog or Mixpanel integration for product analytics

### 7. Auth Hardening
- Swap custom JWT for Keycloak (SSO / SAML / OIDC)
- OpenFGA for row-level access control per campaign (not just role-level)
- Invite-based user onboarding with email verification
- MFA / passkey support

---

## Quick Wins (Pick up anytime)

- Add pagination to the approvals queue
- Add asset type tabs to the Content Factory page (`/content`)
- Show spend vs. budget progress bar on campaign cards
- Campaign duplication — clone a campaign with a new name
- Soft-delete / archive campaigns
- Slack webhook notification when approval is requested or execution fails
- Export audit log to CSV
