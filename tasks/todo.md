# RFI Schema Condensation Refactor

## Status: COMPLETE

## What's Done (this session)
- [x] File upload support (PDF/Word) on Gather page
- [x] Gather page speed: 30s → 1.6s (parallel HubSpot + lightweight Fireflies summaries)
- [x] Extraction: 2 workers, smallest-first sorting, JSON repair, per-job error isolation
- [x] Extraction prompt: distinguish prospect's current state vs MSP recommendations
- [x] Fireflies HubSpot notes filtering (removed duplicate meeting summaries)
- [x] Field updates: incumbent provider question, removed MSP cooperation & transition, backup equipment placement
- [x] Contract type multiselect UI on Gather page
- [x] Previously processed transcripts badge

## Next Task: Condense RFI Fields (~90 → ~65)

User approved the following merges/removals. Implement all at once:

### Company Overview (6 → 5)
- REMOVE `onsite_or_remote` (row 16)
- UPDATE `users_by_location` (row 17) → "Breakdown of users by location (include remote/hybrid workers)"

### Current IT State (5 → 4)
- REMOVE `ticket_stats` (row 24)

### Microsoft 365 & Licensing (7 → 6)
- REMOVE `ms_additional_licensing` (row 28) — merge into `ms_licensing` (row 27)
- UPDATE row 27 hint to include add-on licenses

### Servers & Infrastructure (10 → 5)
- MERGE `server_location` + `offsite_hosted_equipment` + `cloud_servers` → "Where are servers hosted? (onsite, colo, cloud — list each)"
- MERGE `server_count` + `server_roles` + `cloud_server_roles` → "How many servers (physical/virtual/cloud) and what are their roles?"
- KEEP `server_specs`, `virtualization`
- MERGE `server_ownership` + `rented_equipment` → "Who owns the hardware? Any leased/rented equipment to return?"

### Data, Files & Applications (8 → 4)
- MERGE `total_data_size` + `data_migration` → "How much data and how much needs migrating?"
- MERGE `lob_applications` + `saas_inventory` + `standard_apps` → "What applications are in use? (LOB, SaaS, standard desktop)"
- REMOVE `linked_files` (niche)
- KEEP `file_repository`, `lob_app_vendor_contacts`

### Email & Communication (11 → 7)
- MERGE `email_hosting` + `email_migration` → "Where is email hosted and will migration be needed?"
- MERGE `mailbox_count` + `public_folders` → "How many mailboxes (user/shared)? Any public folders?"
- MERGE `phone_system` + `phone_upgrade` → "Current phone system and any plans to change?"
- REMOVE `voice_recording` (niche)
- KEEP `email_security`, `number_of_domains`, `domain_website_hosting`, `collaboration_tools`

### Network & Connectivity (9 → 6)
- MERGE `internet_connectivity` + `isp_management` → "Internet provider/speed — who manages the relationship?"
- MERGE `routers` + `switches` + `waps` → "Network equipment: routers, switches, WAPs (brand/model and count)"
- KEEP `firewalls` (critical, stays separate), `printers_copiers`, `network_diagram`, `other_it_vendors`

### Devices & Endpoints (8 → 5)
- MERGE `windows_devices` + `macos_devices` + `mobile_devices` + `device_ownership` → "Device inventory: Windows, macOS, mobile counts. Corporate or BYOD?"
- KEEP `domain_join`, `device_encryption`, `heavy_workloads`, `asset_register`

### Security & Compliance (13 → 9)
- MERGE `cybersecurity_measures` + `endpoint_protection` → "What cybersecurity and endpoint protection is in place?"
- MERGE `mfa` + `sso_provider` → "What identity management is in place? (MFA, SSO)"
- MERGE `remote_access` + `vpn` + `remote_support_tool` → "Remote access solutions (VPN, virtual desktops, remote support tools)"
- KEEP `mdm`, `patch_management`, `security_awareness_training`, `cyber_insurance`, `compliance_requirements`, `archiving`

### Backup & DR (4) — unchanged
### Documentation & Handoff (2) — unchanged

## Implementation Steps
1. [x] Rewrite `schema/rfi_fields.py` with new condensed fields, renumber all rows cleanly (no gaps)
2. [x] Rebuild `templates/rfi_template.xlsx` to match new row layout (preserve merged cells for section headers)
3. [x] Update `frontend/src/pages/ReviewPage.tsx` getCategory() row ranges (line 23)
4. [x] Test: backend imports, Excel generation round-trip, field count assertions — all pass

## Key Files
- `schema/rfi_fields.py` — field definitions with row numbers
- `templates/rfi_template.xlsx` — Excel template (merged cells A:C for section headers)
- `frontend/src/pages/ReviewPage.tsx` — getCategory() maps rows → sections
- `extraction/extractor.py` — extraction engine (system prompt, parallel workers)
- `output/excel_generator.py` — writes answers into template

## New Row Layout (target)
```
Row 1:  Document header
Row 2:  Engagement header       | Rows 3-10:  8 fields
Row 11: Company header          | Rows 12-16: 5 fields
Row 17: Current IT header       | Rows 18-21: 4 fields
Row 22: M365 & Licensing header | Rows 23-28: 6 fields
Row 29: Servers header          | Rows 30-34: 5 fields
Row 35: Data & Apps header      | Rows 36-39: 4 fields
Row 40: Email & Comms header    | Rows 41-47: 7 fields
Row 48: Network header          | Rows 49-54: 6 fields
Row 55: Devices header          | Rows 56-60: 5 fields
Row 61: Security header         | Rows 62-70: 9 fields
Row 71: Backup & DR header      | Rows 72-75: 4 fields
Row 76: Documentation header    | Rows 77-78: 2 fields
Total: 78 rows, 65 fields
```

## API Rate Limits (Anthropic)
- 10K output tokens/min, 50K input tokens/min, 50 RPM
- 2 parallel workers + smallest-first sorting is optimal for current tier
- Fewer fields = fewer output tokens per job = less throttling
