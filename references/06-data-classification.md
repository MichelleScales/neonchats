# Data Classification Rules

Sourced from `Data.docx`. These rules govern where each data category can flow.

| Category | Examples | Storage | RAG | External LLM |
|---|---|---|---|---|
| Public | Website copy, press releases, public pricing | Postgres + object storage | Yes | Yes |
| Internal (non-sensitive) | Brand voice, approved taglines, campaign briefs (no customer data) | Postgres | Yes | Yes (allowlisted) |
| Confidential (business) | Strategy docs, roadmaps, revenue numbers | Postgres encrypted + object storage | Yes | **No** by default |
| PII | Names, emails, phone numbers, IPs, device IDs | Field-level encryption | Yes (tenant-scoped, minimal) | **No** (only if redacted + policy allows) |
| PHI (HIPAA) | Health info, diagnoses, appointments, insurance IDs | Separate tenant keys, strict retention | Private plane only | **Never** |
| Special category (GDPR) | Health, biometrics, religion, political opinions | Same as PHI tier | Private only | **Never** |
| Credentials / secrets | API keys, passwords, OAuth tokens | Vault only | **No** | **Never** |
| Customer lists | Email lists, phone lists, lead imports | Encrypted tables | Limited | **Never** |
| Raw transcripts | Calls, chat logs, support tickets | Object storage encrypted | Private only | **No** by default |
| Safe summaries | De-identified summaries (no identifiers) | Postgres | Yes | Yes (allowlisted) |
| Metrics / aggregates | CTR, CPA, conversion rate, cohort performance | Postgres | Yes | Yes |

## Key Rules

1. **PHI and credentials are hard blocks** — policy checker enforces `"Never"` regardless of tenant config
2. **Safe summaries** are the bridge pattern: summarize privately → pass only summaries to external LLMs
3. **PII** requires explicit redaction + policy allowlist + logging before going to external LLMs
4. **Confidential business data** defaults to private; can be enabled per tenant by admin

## Where This Is Enforced

- `apps/api/app/services/policy.py` — PII pattern detection, banned phrases, claims checks
- `apps/api/app/services/content_generator.py` — routes to external vs. private based on provider config
- Phase 3: OPA policy engine enforces classification at the gateway level

## The "Safe Summaries" Pattern

```
Raw transcript (PHI/PII)
    → Private model (vLLM in VPC)
    → De-identified summary (no names, IDs, health data)
    → External LLM (Claude, GPT-4o) for generation
    → Generated content reviewed by human before publish
```
