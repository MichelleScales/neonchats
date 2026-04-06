# API Keys & External Services

All keys needed to run the platform in production. None of these are required for local development except Moonshot (content generation) and a database.

---

## ✅ Currently Configured (in .env)

### Moonshot AI (Kimi) — Content Generation
**What it's used for:** Generating all campaign content — emails, social posts, ad copy, landing pages.
**Get it at:** https://platform.moonshot.cn
**Steps:**
1. Sign up at platform.moonshot.cn
2. Go to API Keys → Create Key
3. Add to `.env`: `MOONSHOT_API_KEY=sk-...`

**Env vars:**
```
MOONSHOT_API_KEY=sk-...
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
DEFAULT_MODEL_PROVIDER=moonshot
DEFAULT_EXTERNAL_MODEL=moonshot-v1-8k
```

**Models available:** `moonshot-v1-8k`, `moonshot-v1-32k`, `moonshot-v1-128k` (longer context = higher cost)

---

## 🔧 Phase 1/2 Integrations (env-level keys)

### SendGrid — Email Delivery
**What it's used for:** Transactional email sends from the execution engine.
**Get it at:** https://app.sendgrid.com
**Steps:**
1. Sign up / log in
2. Settings → API Keys → Create API Key → Full Access
3. Add to `.env`: `SENDGRID_API_KEY=SG....`

**Env vars:**
```
SENDGRID_API_KEY=SG....
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

**Note:** Your from email domain must be verified in SendGrid (Settings → Sender Authentication).

---

### HubSpot — CRM Contact Lists
**What it's used for:** Pulling contact email lists for targeted email sends.
**Get it at:** https://app.hubspot.com
**Steps:**
1. Settings → Integrations → Private Apps → Create a private app
2. Scopes required: `crm.lists.read`, `crm.objects.contacts.read`
3. Copy the access token
4. Add to `.env`: `HUBSPOT_ACCESS_TOKEN=pat-...`

**Env vars:**
```
HUBSPOT_ACCESS_TOKEN=pat-na1-...
```

---

## 🔌 Phase 3 MCP Gateway Connectors (stored via /api/connectors/credentials)

These are stored in the database per-tenant via the Integrations page, not in `.env`.

---

### Klaviyo — Email & SMS Campaigns
**What it's used for:** Email and SMS campaign sends to Klaviyo lists.
**Get it at:** https://www.klaviyo.com/account#api-keys-tab
**Steps:**
1. Account → Settings → API Keys → Create Private API Key
2. Scopes: Full access or at minimum `Lists: Read`, `Campaigns: Write`
3. Enter at `/integrations` → Klaviyo → Configure

**Credential fields:**
```
api_key       → Private API Key (pk_...)
list_id       → Default Klaviyo List ID (from Lists & Segments)
from_email    → Sender email address
from_label    → Sender display name
```

---

### Meta Ads — Facebook & Instagram
**What it's used for:** Creating ad creatives and ads in existing Meta ad sets.
**Get it at:** https://developers.facebook.com/apps
**Steps:**
1. Create a Meta App at developers.facebook.com → Business type
2. Add "Marketing API" product to your app
3. Generate a User Access Token with scopes: `ads_management`, `ads_read`, `pages_manage_ads`
4. For production: convert to a System User token (doesn't expire) via Business Manager → System Users
5. Find your Ad Account ID in Meta Business Manager → Accounts → Ad Accounts (format: `act_XXXXXXXXX`, enter without `act_`)
6. Enter at `/integrations` → Meta Ads → Configure

**Credential fields:**
```
access_token  → User or System User access token
ad_account_id → Your ad account ID (numbers only, no "act_")
page_id       → Your Facebook Page ID
```

**Note:** Ads are created with status `PAUSED` — you activate them manually in Meta Ads Manager or via the API.

---

### Google Ads — Search Ads (RSA)
**What it's used for:** Creating responsive search ads in existing Google Ads ad groups.
**Get it at:** https://developers.google.com/google-ads/api/docs/start
**Steps:**
1. Apply for a Google Ads Developer Token: https://developers.google.com/google-ads/api/docs/first-call/dev-token
   - Takes 1–3 business days to approve for basic access
2. Create OAuth credentials: https://console.cloud.google.com → APIs & Services → Credentials → OAuth 2.0 Client ID (Desktop app)
3. Get a refresh token using the OAuth playground or `google-auth-oauthlib`: scope `https://www.googleapis.com/auth/adwords`
4. Your Customer ID is in the top-right of Google Ads Manager (format: `123-456-7890`)
5. Enter at `/integrations` → Google Ads → Configure

**Credential fields:**
```
developer_token → From Google Ads API Centre
client_id       → OAuth 2.0 Client ID
client_secret   → OAuth 2.0 Client Secret
refresh_token   → Long-lived OAuth refresh token
customer_id     → Google Ads Customer ID (e.g. 1234567890)
```

**Note:** Ads created with status `PAUSED`. Google Ads requires a Test Account during development — production sends require applying for Standard access.

---

### Webflow — Landing Pages
**What it's used for:** Publishing landing page content as CMS items.
**Get it at:** https://webflow.com/dashboard → Project Settings → Integrations → API Access
**Steps:**
1. Open your Webflow project → Settings → Integrations
2. Generate a Site API Key (v2)
3. Find your Site ID: Settings → General → Site ID
4. Create a CMS Collection for landing pages and note its Collection ID (visible in the CMS panel URL)
5. Ensure your collection has fields: `name`, `slug`, `headline`, `body`, `cta`
6. Enter at `/integrations` → Webflow → Configure

**Credential fields:**
```
api_key        → Site API Key
site_id        → Webflow Site ID
collection_id  → CMS Collection ID for landing pages
```

---

## 🧠 Optional: Alternative LLM Providers

The platform supports swapping the LLM provider via `.env`. All use the OpenAI-compatible SDK.

### Anthropic (Claude)
**Get it at:** https://console.anthropic.com
```
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL_PROVIDER=anthropic
DEFAULT_EXTERNAL_MODEL=claude-sonnet-4-6
```

### OpenAI (GPT-4o)
**Get it at:** https://platform.openai.com/api-keys
```
OPENAI_API_KEY=sk-...
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_EXTERNAL_MODEL=gpt-4o
```

### Other OpenAI-compatible providers (Groq, DeepSeek, Together AI, Mistral, local Ollama)
Follow the pattern in `references/05-llm-providers.md`. Point `MOONSHOT_BASE_URL` at the provider and set the model name.

---

## 📊 Optional: Analytics & Monitoring (Phase 4)

These are not yet wired up but listed for planning:

| Service | Purpose | URL |
|---|---|---|
| PostHog | Product analytics, funnel tracking | https://posthog.com |
| Sentry | Error monitoring + performance | https://sentry.io |
| Datadog | Infrastructure + APM | https://datadoghq.com |
| Resend | Alternative to SendGrid (simpler) | https://resend.com |

---

## 🔑 Environment Variables — Full Reference

```env
# ── Content Generation ────────────────────────────────────────────────────────
MOONSHOT_API_KEY=sk-...                   # required for content generation
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
DEFAULT_MODEL_PROVIDER=moonshot
DEFAULT_EXTERNAL_MODEL=moonshot-v1-8k

ANTHROPIC_API_KEY=                        # optional fallback
OPENAI_API_KEY=                           # optional fallback

# ── Email (Phase 1/2) ─────────────────────────────────────────────────────────
SENDGRID_API_KEY=SG....
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# ── CRM (Phase 2) ────────────────────────────────────────────────────────────
HUBSPOT_ACCESS_TOKEN=pat-...

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://emp:emp@localhost:5432/emp
DATABASE_SYNC_URL=postgresql://emp:emp@localhost:5432/emp

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Auth ──────────────────────────────────────────────────────────────────────
SECRET_KEY=your-long-random-string-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── App ───────────────────────────────────────────────────────────────────────
APP_ENV=development
APP_URL=http://localhost:3000
API_URL=http://localhost:8000
CORS_ORIGINS=["http://localhost:3000"]
```

**Phase 3 connector credentials (Klaviyo, Meta, Google Ads, Webflow) are stored in the database via the Integrations page — not in `.env`.**
