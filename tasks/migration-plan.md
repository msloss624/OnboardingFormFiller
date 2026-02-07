# Full Web App Migration: FastAPI + React + Azure

## Status

- **Phase 1: FastAPI Backend + Database** — COMPLETE
- **Phase 2: Azure Infrastructure + Blob Storage** — COMPLETE
- **Phase 3: Microsoft SSO (MSAL)** — COMPLETE
- **Phase 4: React Frontend** — COMPLETE
- **Phase 5: Extraction Quality Improvements** — NOT STARTED
- **Phase 6: UX Polish** — NOT STARTED

## Architecture

```
React SPA (frontend/) → FastAPI Backend (backend/) → Azure SQL + Blob + Azure AD
```

Local dev: SQLite + local filesystem + dev user (no auth). Azure: just set env vars.

## Project Structure

```
OnboardingFormFiller/
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Extended config with DATABASE_URL, BLOB, Azure AD
│   ├── database.py              # SQLAlchemy async engine + session
│   ├── models.py                # User + Run SQLAlchemy models
│   ├── auth.py                  # Azure AD JWT validation + dev fallback
│   ├── storage.py               # Azure Blob helpers + local fallback
│   ├── routes/
│   │   ├── deals.py             # GET /api/deals/search, GET /api/deals/{id}/context
│   │   ├── transcripts.py       # GET /api/transcripts?domain=...
│   │   ├── extraction.py        # POST /api/runs, GET /api/runs/{id}, PUT answers, retry-field
│   │   ├── exports.py           # GET /api/runs/{id}/excel, GET /api/runs (list)
│   │   └── auth_routes.py       # GET /api/me
│   └── services/
│       └── extraction_service.py  # Background extraction orchestration
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Router + layout + step indicator
│   │   ├── auth/MsalProvider.tsx # MSAL wrapper (skips in dev)
│   │   ├── api/client.ts        # Axios wrapper with all types
│   │   ├── pages/               # SearchPage, GatherPage, ExtractingPage, ReviewPage, HistoryPage
│   │   └── components/          # DealCard, TranscriptCheckbox, AnswerEditor, ConfidenceBadge, DiffView
│   └── staticwebapp.config.json
├── clients/                     # REUSED AS-IS from Streamlit
├── extraction/extractor.py      # REUSED AS-IS — Claude extraction engine
├── output/excel_generator.py    # REUSED AS-IS — Excel generation
├── schema/rfi_fields.py         # REUSED AS-IS — 92-field RFI schema
└── templates/rfi_template.xlsx
```

## Phase 5: Extraction Quality Improvements (NEXT)

### 1. Field-level re-extraction (`POST /api/runs/{id}/retry-field`)
- Takes a single field_key + optional prompt_hint
- Re-runs Claude against ALL sources stored on the run for just that one field
- Uses a more aggressive prompt: "look harder for X, consider synonyms, related terms..."
- Updates that one answer in the run's answers_json
- Route stub exists in `backend/routes/extraction.py` (line ~110, currently returns 501)
- Needs a new method on `RFIExtractor` in `extraction/extractor.py`

### 2. Confidence calibration pass
- After initial extraction in `extraction_service.py`, run a second Claude call
- Prompt: "For each HIGH/MEDIUM answer below, does the evidence actually support the answer?"
- Downgrade overconfident answers (HIGH → MEDIUM if evidence is weak)
- Add as a method on `RFIExtractor`, call it from `extraction_service.py` between steps 5 and 6

### 3. Smarter chunking (`extraction/extractor.py`)
- `_chunk_text()` currently splits on paragraph boundaries (`\n\n`)
- Fireflies transcripts use `**Speaker Name**: text` format (from `FullTranscript.full_text`)
- New approach: detect speaker turns, split at speaker boundaries, keep Q&A pairs together
- Falls back to current paragraph-based chunking for non-transcript sources
- Detection: check if text contains `**` speaker markers

## Phase 6: UX Polish (AFTER Phase 5)

### 1. Diff view on re-run
- When baseline_run_id is set, ReviewPage shows "Changes" tab
- Uses the existing `DiffView.tsx` component (already built)
- Shows: newly filled (green), upgraded confidence (blue), conflicts (yellow)

### 2. Bulk category review
- "Mark all as reviewed" button per category in ReviewPage
- Reviewed answers get a `reviewed: true` flag in answers_json
- Protected from future re-runs

### 3. Export history timeline
- HistoryPage shows all runs for a deal as timeline
- Date, user, completion %, download link
- Compare any two runs side-by-side

### 4. Real-time extraction progress (SSE)
- Replace polling in ExtractingPage with Server-Sent Events
- FastAPI streams: "Processing transcript 1/3...", "Merging answers...", "Done."
- Use `StreamingResponse` with `text/event-stream` content type

## Key Technical Notes
- Python 3.9: use `Optional[str]` not `str | None` in SQLAlchemy Mapped[] annotations
- Pydantic v2 with `from __future__ import annotations` handles `str | None` fine
- TypeScript strict mode: use `import type` for type-only imports (verbatimModuleSyntax)
- Tailwind v4 via `@tailwindcss/vite` plugin
- Backend: `python3 -m uvicorn backend.main:app --port 8000`
- Frontend: `cd frontend && npm run dev` (proxies /api to :8000)
