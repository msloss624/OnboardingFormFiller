# Full Web App Migration: FastAPI + React + Azure

## Status

- **Phase 1: FastAPI Backend + Database** — COMPLETE
- **Phase 2: Azure Infrastructure + Blob Storage** — COMPLETE
- **Phase 3: Microsoft SSO (MSAL)** — COMPLETE
- **Phase 4: React Frontend** — COMPLETE
- **Phase 5: Extraction Quality + UX** — COMPLETE
- **Phase 6: Email to Account Team** — COMPLETE (Graph API live, sends from info@belltec.com)

## Architecture

```
React SPA (frontend/)  →  FastAPI Backend (backend/)  →  SQLite + Azure Blob + Azure AD
```

Local dev: SQLite + local filesystem + dev user (no auth) + email dry-run mode.
Azure: set env vars for Blob, Azure AD, and Graph API.

## Key Technical Notes
- Python 3.9 locally, 3.11 on Azure
- Use `Optional[str]` not `str | None` in SQLAlchemy Mapped[] annotations
- TypeScript strict mode: use `import type` for type-only imports
- Tailwind v4 via `@tailwindcss/vite` plugin
- Backend: `python3 -m uvicorn backend.main:app --port 8000`
- Frontend: `cd frontend && npm run dev` (proxies /api to :8000)
- Claude extraction: 2 parallel workers (4 causes 429s)
- Graph API: client credentials flow, dry-run when secret not configured
