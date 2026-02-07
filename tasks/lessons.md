# Lessons Learned

## Fireflies API

1. **GraphQL field names matter** — The `transcript` query uses `speakers.name`, NOT `speakers.displayName`. The API returns 400 errors for invalid field names with no helpful error message.

2. **Date field is a timestamp (int)** — Not a string. Handle with: `str(t.date)[:10] if isinstance(t.date, str) else "Recent"`

3. **Search by participant email is most reliable** — Keyword search returns inconsistent results. Always use participant email when available.

## HubSpot API

1. **Legacy API keys are deprecated** — Must use Private App tokens (format: `pat-na1-...`). Create at Settings → Integrations → Private Apps.

2. **Required scopes for Private App**: `crm.objects.contacts.read`, `crm.objects.companies.read`, `crm.objects.deals.read`

3. **Pipeline filtering** — Use `filterGroups` in search body to filter by pipeline name (e.g., "Outside Sales").

## Streamlit

1. **Enter key submission** — Wrap inputs in `st.form()` with `st.form_submit_button()` to enable Enter key.

2. **Session state for caching** — Use `None` vs `[]` to distinguish "not searched yet" from "searched but empty results".

3. **Back button preservation** — Don't clear session state on back navigation; only clear when selecting a NEW item.

4. **Custom theming** — Use `.streamlit/config.toml` for colors, and `st.markdown()` with `<style>` tags for advanced CSS.

## Python Compatibility

1. **Type hints `str | None`** — Requires Python 3.10+ OR `from __future__ import annotations` at top of file for older versions.

## Azure Deployment

1. **Port must match** — Startup command port and `WEBSITES_PORT` env var must both be `8501` for Streamlit.

2. **SCM Basic Auth** — Must be enabled in Azure for zip deploy to work.

3. **Don't install in startup command** — Dependencies should install during build phase, not startup (too slow).

## Workflow

1. **Test locally first** — Don't push to Azure until all features are working locally.

2. **Debug with print statements** — Add them liberally, then remove before committing.
