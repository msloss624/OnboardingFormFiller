# Onboarding Form Filler

## What This Is
A Streamlit web app that auto-fills the 87-field IT infrastructure RFI template using data pulled from HubSpot and Fireflies.ai meeting transcripts. Claude (Anthropic API) reads the transcripts and extracts answers to each RFI question with confidence scoring.

**Use case:** When a deal closes in HubSpot, someone opens this app, selects the deal, and gets a pre-filled RFI Excel spreadsheet in ~2 minutes instead of 20+ minutes of manual work.

---

## Architecture & Data Flow

```
User selects deal in Streamlit UI
        ↓
HubSpot API: pull company info + associated contacts
        ↓
Extract client email domain from contacts (e.g. @randrbrands.com)
        ↓
Fireflies API: search transcripts by participant email domain
        ↓
Retrieve full transcripts (not just summaries — summaries miss too much detail)
        ↓
User can also paste URLs or upload additional docs
        ↓
Claude API: extract answers to all 87 RFI fields from all sources
        ↓
Merge answers (HubSpot structured > high confidence AI > medium > low)
        ↓
Review screen: user can edit any answer before export
        ↓
Generate color-coded Excel (green/yellow/pink/gray by confidence)
        ↓
Download filled RFI
```

## Key Findings From Data Exploration

These findings shaped the architecture (explored using R&R Brands as test case):

1. **Fireflies keyword search is unreliable.** Searching "R&R Brands" and "randrbrands" returned zero results. Searching by participant email (ryan@randrbrands.com) returned 8 transcripts. **Always search by participant email, not keywords.**

2. **Full transcripts >> summaries.** The Fireflies summary for the R&R initial discovery call captured maybe 30% of the RFI-relevant detail. The full transcript had specific product names (Lenovo, Toast, Aloha), server contract details, email tenant issues, Windows licensing specifics — exactly what the RFI asks about.

3. **HubSpot structured fields are thin.** Company name, location, employee count, domain — that's about it. The real data lives in transcripts.

4. **HubSpot notes require opt-in.** The engagement/notes API needs to be enabled in HubSpot settings. The Fireflies-posted summaries in HubSpot notes are mostly redundant with going to Fireflies directly, but could be a useful fallback.

5. **The flow is: HubSpot → contacts → domain → Fireflies → full transcripts → Claude extraction.** This is the most reliable path to getting transcript data matched to the right client.

---

## Project Structure

```
OnboardingFormFiller/
├── app.py                          # Streamlit UI — 4-step flow (search → gather → extract → review)
├── config.py                       # Reads API keys from environment variables
├── requirements.txt                # Python dependencies (6 packages)
├── Dockerfile                      # For Azure Container deployment (optional)
├── .env.example                    # Template for local development
├── .gitignore
├── .streamlit/
│   └── config.toml                 # Streamlit theme and server config
├── schema/
│   └── rfi_fields.py               # All 87 RFI fields mapped with categories, extraction hints,
│                                    # HubSpot property names, and Excel row positions
├── clients/
│   ├── hubspot_client.py           # HubSpot API: deal search, company/contact retrieval,
│   │                                # domain extraction, notes fetching
│   └── fireflies_client.py         # Fireflies GraphQL API: participant email search,
│                                    # full transcript retrieval, domain-based search
├── extraction/
│   └── extractor.py                # Claude API extraction engine:
│                                    # - Category-specific prompts for each RFI field
│                                    # - Confidence scoring (high/medium/low/missing)
│                                    # - Multi-source extraction and merging
│                                    # - Conflict detection across sources
├── output/
│   └── excel_generator.py          # Fills RFI template with extracted answers:
│                                    # - Color-coded cells by confidence
│                                    # - Notes column with source + evidence quotes
│                                    # - Metadata sheet with legend and per-field breakdown
└── templates/
    └── rfi_template.xlsx           # Original RFI template (87 rows, 3 columns)
```

---

## Environment Variables

| Name | Description |
|------|-------------|
| `HUBSPOT_API_KEY` | HubSpot Private App access token (needs contacts.read, companies.read, deals.read scopes) |
| `FIREFLIES_API_KEY` | Fireflies.ai API key (from Integrations → API & Webhooks) |
| `ANTHROPIC_API_KEY` | Anthropic API key (from console.anthropic.com — separate from Claude chat subscription) |
| `WEBSITES_PORT` | `8501` (tells Azure which port Streamlit runs on) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` (tells Azure to install Python packages on deploy) |

---

## Deployment

**Currently deployed to:** Azure App Service (Web App named `OnboardingFormFiller`)
**GitHub repo:** `OnboardingFormFiller` (private)
**Auto-deploys:** Yes — pushing to `main` branch triggers Azure deployment via GitHub Actions

### Azure startup command
```
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0 --server.headless true
```
This must be set in Azure Portal → App Service → Configuration → General settings → Startup Command.

### To redeploy after code changes
Just push to GitHub. Azure picks it up automatically.

---

## How the Extraction Works

The extractor (`extraction/extractor.py`) sends each transcript to Claude with a structured prompt containing all 87 RFI field definitions and their "extraction hints" (what to look for). Claude returns a JSON array with an answer, confidence level, and evidence quote for each field.

When multiple transcripts are processed, the merger picks the best answer per field:
1. HubSpot structured data (highest priority for fields it covers)
2. High-confidence transcript extraction
3. Medium-confidence extraction
4. Low-confidence extraction
5. If multiple high-confidence answers conflict, flags as "CONFLICTING" with both values

### Confidence colors in Excel output
- 🟢 Green = high confidence (explicitly stated with specific details)
- 🟡 Yellow = medium confidence (mentioned but vague, or inferred)
- 🔴 Pink = low confidence (indirect reference, educated guess)
- ⬜ Gray = missing (not found in any source)

---

## RFI Field Categories

The 87 fields are organized into these categories (defined in `schema/rfi_fields.py`):

- **General** — company name, location, users, devices, pain points
- **Current State** — current MSP, support type, ticket volume, business hours
- **Microsoft Licensing** — M365 plans, quantities, contract terms, tenants
- **Google Workspace** — Google licensing
- **3rd Party Licensing** — other MSP-provided software
- **Asset Management** — asset register/inventory
- **Servers (On-Prem)** — hosting location, count, roles, specs, virtualization, DR
- **Servers (Cloud)** — Azure/AWS presence and roles
- **Data & Files** — file storage, data size, migration needs, LOB apps
- **Cybersecurity** — security stack, MFA, MDM, endpoint protection
- **Remote Access** — VPN, remote desktop, Citrix/AVD
- **Email** — hosting, migration, mailbox count, security, domains, backup
- **Compliance** — regulatory requirements, archiving
- **Devices** — Windows/Mac/mobile counts, ownership, domain join, encryption
- **Collaboration** — Teams, Slack, file sharing tools
- **Network** — ISP, firewalls, routers, switches, WAPs, network diagram
- **Phone** — phone system, upgrade plans, voice recording

---

## What's Not Built Yet (Phase 2)

- **SharePoint/OneDrive integration** — pull Word docs from SharePoint as additional source material (needs Microsoft Graph API setup with app registration)
- **URL fetching** — auto-fetch content from pasted URLs (currently accepts pasted text but doesn't crawl URLs)
- **Email sending** — auto-email the completed RFI to the onboarding team via Graph API
- **HubSpot notes** — requires engagement opt-in in HubSpot settings to access notes API

---

## Running Locally (for development)

```bash
cd OnboardingFormFiller
pip install -r requirements.txt
cp .env.example .env  # Fill in your 3 API keys
streamlit run app.py
```

Opens at http://localhost:8501

---

## Current Status (Updated 2026-02-06)

### What's done:
- ✅ All app code written and tested locally
- ✅ GitHub repo created (`OnboardingFormFiller`, private)
- ✅ Azure Web App created and deployed (B1 plan, Python 3.11, Linux)
- ✅ Environment variables set in Azure
- ✅ GitHub connected to Azure Deployment Center (auto-deploys on push to main)
- ✅ **HubSpot pipeline filter** — only queries "Outside Sales" pipeline deals
- ✅ **Fireflies fix** — GraphQL query corrected (`speakers.name` not `displayName`)
- ✅ **UI/UX improvements** — Bellwether branding (#1E4488 blue, #F78E28 orange), step indicator
- ✅ **Enter key search** — form wrapper enables Enter to submit
- ✅ **Back button fix** — preserves cached data when navigating back

### To run locally:
```bash
cd OnboardingFormFiller
pip install -r requirements.txt
# Ensure .env has your 3 API keys (see .env.example)
streamlit run app.py
```
Opens at http://localhost:8501

### To deploy to Azure:
Push to `main` branch — Azure picks it up automatically via GitHub Actions.

### Azure startup command (already configured):
```
python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

### Next steps (Phase 2):
- ⬜ SharePoint/OneDrive integration for additional source docs
- ⬜ URL fetching — auto-crawl pasted URLs
- ⬜ Email sending — auto-email completed RFI via Graph API

---

## Cost Estimates

- **Azure App Service (B1):** ~$13/month
- **Claude API per RFI generation:** ~$0.30–0.75 (depends on transcript volume)
- **At 1 RFI/week:** ~$15–16/month total
