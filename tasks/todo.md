# Onboarding Form Filler - Changes To Do

## Completed Changes

1. **Filter HubSpot to Outside Sales pipeline only** ✅
   - Added pipeline filter to `search_deals()` in `clients/hubspot_client.py`

2. **Fix Fireflies not returning meetings** ✅
   - Fixed GraphQL query: `speakers.displayName` → `speakers.name`
   - Fixed date formatting for int timestamps

3. **Improve frontend UI/UX** ✅
   - Added Bellwether branding (colors: #1E4488 blue, #F78E28 orange)
   - Added step indicator component
   - Custom CSS for cards, headers, metrics
   - Updated `.streamlit/config.toml` with brand colors

4. **Enter key should trigger search on first page** ✅
   - Added `st.form()` wrapper to enable Enter key submission

5. **Back button shouldn't reload everything** ✅
   - Preserve cached data when navigating back

6. **Removed debug print statements** ✅
   - Cleaned up `clients/fireflies_client.py`

---

## Ready for Testing

All items complete. Test locally before deploying to Azure.

