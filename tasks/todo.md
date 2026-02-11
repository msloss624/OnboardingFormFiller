# Current Status

## Completed
- [x] FastAPI backend + SQLAlchemy async database
- [x] Azure Blob Storage for Excel exports
- [x] Microsoft SSO (MSAL v5 redirect flow)
- [x] React frontend (5-step workflow)
- [x] HubSpot deal search + company/contact context
- [x] Fireflies transcript search by participant email
- [x] File upload support (PDF/Word)
- [x] Claude extraction with 2 parallel workers
- [x] RFI field condensation (90 → 65 fields)
- [x] Color-coded Excel generation
- [x] Field-level re-extraction (retry individual fields)
- [x] Contract type multi-select on Gather page
- [x] Send to Account Team email feature (Phase 6)
- [x] Editable email preview with live rendering
- [x] HubSpot deal owner lookup for recipients
- [x] SOW/MSA file attachment support
- [x] GitHub Actions OIDC deployment
- [x] Legacy Streamlit code cleanup

## Pending
- [x] Graph API admin consent (granted by Corey Crossman, 2026-02-10)
- [x] Generate client secret for Graph API (created 2026-02-10, expires 2028)
- [x] Set Graph env vars on Azure App Service (GRAPH_CLIENT_ID, GRAPH_TENANT_ID, GRAPH_CLIENT_SECRET, GRAPH_SEND_FROM_EMAIL)
- [x] Test email sending end-to-end in production (verified 2026-02-10, sends from info@belltec.com)
- [ ] Application Access Policy to restrict Mail.Send to info@belltec.com (optional hardening)

## Future Improvements (deferred)
- [ ] User ownership checks on runs (when multi-user needed)
- [ ] Rate limiting (low priority with auth in place)
- [ ] HubSpot/Fireflies response caching
- [ ] Real-time extraction progress (SSE instead of polling)
- [ ] Run comparison (diff view between two runs)
