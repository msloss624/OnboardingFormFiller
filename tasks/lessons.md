# Lessons Learned

## Fireflies API

1. **GraphQL field names matter** — The `transcript` query uses `speakers.name`, NOT `speakers.displayName`. The API returns 400 errors for invalid field names with no helpful error message.

2. **Date field is a timestamp (int)** — Not a string. Handle with: `str(t.date)[:10] if isinstance(t.date, str) else "Recent"`

3. **Search by participant email is most reliable** — Keyword search returns inconsistent results. Always use participant email when available.

## HubSpot API

1. **Legacy API keys are deprecated** — Must use Private App tokens (format: `pat-na1-...`). Create at Settings > Integrations > Private Apps.

2. **Required scopes for Private App**: `crm.objects.contacts.read`, `crm.objects.companies.read`, `crm.objects.deals.read`

3. **Pipeline filtering** — Use `filterGroups` in search body to filter by pipeline name (e.g., "Outside Sales").

4. **Owner lookup** — `crm.objects.owners.read` scope is needed for `get_owner_email()`. Without it, owner lookups return 403.

## Azure AD / MSAL

1. **Token version** — `requestedAccessTokenVersion` defaults to null (v1). Set to 2 for v2. Backend accepts both formats.

2. **MSAL v5** — Requires explicit `initialize()` before any operations. Use redirect flow, not popup.

3. **Application permissions** — `Mail.Send` and other high-privilege permissions require Global Administrator to grant admin consent. Application Administrator role is not sufficient.

4. **SMTP AUTH** — Disabled by default on M365 tenants. Server won't even advertise AUTH capability. Requires Exchange Admin to enable.

## Azure Deployment

1. **Persistent storage** — Only `/home` survives restarts on App Service. SQLite DB must live there.

2. **OIDC deploy** — More reliable than SCM basic auth. Use service principal with federated credentials.

3. **Env var changes** — Trigger container swap, can kill in-flight requests. Plan accordingly.

4. **Deploy time** — ~10 min total (1 min build, 9 min deploy). Don't wait for it.

## Python

1. **Type hints `str | None`** — Use `Optional[str]` in SQLAlchemy `Mapped[]` annotations for Python 3.9 compat. Pydantic v2 with `from __future__ import annotations` handles `str | None` fine.

## Frontend

1. **TypeScript strict mode** — Use `import type` for type-only imports (verbatimModuleSyntax).

2. **Tailwind v4** — Use `@import "tailwindcss"` not directives. Via `@tailwindcss/vite` plugin.

3. **Auth headers on downloads** — `<a href>` anchor tags don't send Authorization headers. Use axios with `responseType: 'blob'` + programmatic download instead.

## Extraction

1. **Parallelism** — 2 workers is optimal. 4 causes 429 rate limits from Anthropic.

2. **Prompt design** — Distinguish prospect's current state vs MSP recommendations. Claude sometimes conflates what the client has with what Bellwether plans to provide.
