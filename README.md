# Onboarding Form Filler

## What This Is
A web app that auto-fills the 65-field IT infrastructure onboarding workbook using data pulled from HubSpot deals, Fireflies.ai meeting transcripts, and uploaded documents. Claude (Anthropic API) reads all sources and extracts answers with confidence scoring. The filled workbook can then be emailed directly to the account team.

**Use case:** When a deal closes in HubSpot, someone opens this app, selects the deal, and gets a pre-filled onboarding Excel in ~2 minutes instead of 20+ minutes of manual work — then sends it to the team with one click.

**Production URL:** https://onboardingformfiller.azurewebsites.net

---

## Architecture

```
React SPA (frontend/)  →  FastAPI Backend (backend/)  →  SQLite + Azure Blob + Azure AD

5-step workflow:
  1. Search    — find a HubSpot deal
  2. Gather    — select transcripts, upload docs, set contract type
  3. Extract   — Claude extracts answers (parallel, ~2 min)
  4. Review    — edit answers, download Excel
  5. Send      — compose & send email to account team via Graph API
```

### Data Flow
```
HubSpot API: deal → company → contacts → email domain
        ↓
Fireflies API: search transcripts by participant email domain
        ↓
User selects transcripts + uploads additional docs (PDF/Word)
        ↓
Claude API: extract answers to 65 fields from all sources (2 parallel workers)
        ↓
Merge answers (HubSpot structured > high confidence > medium > low)
        ↓
Review: edit any answer, retry individual fields, download Excel
        ↓
Send: editable email preview → Graph API → account team
```

---

## Project Structure

```
OnboardingFormFiller/
├── backend/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── config.py                  # Environment-based config
│   ├── database.py                # SQLAlchemy async engine + migrations
│   ├── models.py                  # User + Run models
│   ├── auth.py                    # Azure AD JWT validation + dev fallback
│   ├── storage.py                 # Azure Blob + local filesystem fallback
│   ├── routes/
│   │   ├── deals.py               # Deal search + context
│   │   ├── transcripts.py         # Fireflies transcript lookup
│   │   ├── extraction.py          # Run creation, status, answers, retry
│   │   ├── exports.py             # Excel download, run history
│   │   ├── email.py               # Email preview + send via Graph API
│   │   └── auth_routes.py         # GET /api/me
│   └── services/
│       ├── extraction_service.py  # Background extraction orchestration
│       └── graph_email.py         # Graph API email client + HTML builder
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Router + layout + 5-step indicator
│   │   ├── auth/MsalProvider.tsx  # MSAL v5 redirect flow
│   │   ├── api/client.ts          # Axios client with all types
│   │   ├── pages/
│   │   │   ├── SearchPage.tsx     # Step 1: deal search
│   │   │   ├── GatherPage.tsx     # Step 2: data sources + contract type
│   │   │   ├── ExtractingPage.tsx # Step 3: progress polling
│   │   │   ├── ReviewPage.tsx     # Step 4: edit answers + download
│   │   │   ├── SendEmailPage.tsx  # Step 5: email compose + preview
│   │   │   └── HistoryPage.tsx    # Past runs
│   │   └── components/            # AnswerEditor, ConfidenceBadge, DiffView, etc.
│   └── vite.config.ts
├── clients/
│   ├── hubspot_client.py          # HubSpot CRM API
│   └── fireflies_client.py        # Fireflies GraphQL API
├── extraction/
│   └── extractor.py               # Claude extraction engine
├── output/
│   └── excel_generator.py         # Color-coded Excel generation
├── schema/
│   └── rfi_fields.py              # 65-field schema with categories + hints
└── templates/
    └── rfi_template.xlsx          # Excel template
```

---

## Environment Variables

| Name | Required | Description |
|------|----------|-------------|
| `HUBSPOT_API_KEY` | Yes | HubSpot Private App token (`pat-na1-...`) |
| `FIREFLIES_API_KEY` | Yes | Fireflies.ai API key |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `DATABASE_URL` | No | SQLAlchemy connection string (defaults to local SQLite) |
| `BLOB_CONNECTION_STRING` | No | Azure Blob Storage (local filesystem fallback) |
| `AZURE_AD_TENANT_ID` | No | Azure AD tenant for SSO (dev mode skips auth) |
| `AZURE_AD_CLIENT_ID` | No | Azure AD app registration client ID |
| `AZURE_AD_AUDIENCE` | No | JWT audience for token validation |
| `GRAPH_CLIENT_ID` | No | App registration ID with `Mail.Send` permission |
| `GRAPH_TENANT_ID` | No | Azure AD tenant ID for Graph API |
| `GRAPH_CLIENT_SECRET` | No | Client secret for Graph API (dry-run if missing) |
| `GRAPH_SEND_FROM_EMAIL` | No | Mailbox to send from (e.g. info@belltec.com) |
| `ONBOARDING_TEAM_EMAIL` | No | Default recipient for account team emails |

---

## Running Locally

```bash
cd OnboardingFormFiller

# Backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn backend.main:app --port 8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

App opens at http://localhost:5173 (proxies `/api` to backend on :8000).

Email sending runs in dry-run mode locally (logs payload, doesn't send) unless `GRAPH_CLIENT_SECRET` is set.

---

## Deployment

Deployed to **Azure App Service** (B1 Linux, Python 3.11) in the `Sales_Automations` resource group.

Push to `main` triggers GitHub Actions (OIDC auth) which builds the frontend, packages the backend, and deploys. Takes ~10 minutes.

### Azure Resources
- **App Service:** OnboardingFormFiller (canadacentral)
- **Storage Account:** onboardingffstorage (container: exports)
- **App Registration:** OnboardingFormFiller (SSO + Graph API)

---

## How Extraction Works

The extractor sends transcripts to Claude in category-based batches (2 parallel workers). Each batch includes the relevant field definitions with extraction hints. Claude returns JSON with an answer, confidence level, and evidence quote per field.

Multi-source merging priority:
1. HubSpot structured data (highest for fields it covers)
2. High-confidence transcript extraction
3. Medium-confidence extraction
4. Low-confidence extraction

### Confidence Colors in Excel
- Green = high confidence (explicitly stated)
- Yellow = medium confidence (mentioned but vague)
- Pink = low confidence (inferred)
- Gray = missing (not found)

---

## Cost Estimates

- **Azure App Service (B1):** ~$13/month
- **Claude API per extraction:** ~$0.30-0.75 (depends on transcript volume)
- **At 1 run/week:** ~$15-16/month total
