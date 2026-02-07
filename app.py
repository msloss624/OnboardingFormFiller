"""
Onboarding Form Filler — Streamlit App
Search a HubSpot deal, pull transcripts, extract answers, generate filled form.
"""
from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from datetime import datetime

import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from clients.hubspot_client import HubSpotClient
from clients.fireflies_client import FirefliesClient
from extraction.extractor import RFIExtractor, merge_answers, ExtractedAnswer
from output.excel_generator import generate_rfi_excel
from schema.rfi_fields import RFI_FIELDS, Confidence

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Onboarding Form Filler | Bellwether",
    page_icon="🔔",
    layout="wide",
)

# ── Custom CSS for Bellwether branding ────────────────────────────────
st.markdown("""
<style>
    /* Bellwether brand colors */
    :root {
        --bellwether-blue: #1E4488;
        --bellwether-orange: #F78E28;
        --bellwether-light: #F5F5FC;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1E4488 0%, #2a5298 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 {
        color: white !important;
        margin: 0 !important;
        font-size: 1.8rem !important;
    }
    .main-header p {
        color: rgba(255,255,255,0.85);
        margin: 0.5rem 0 0 0;
        font-size: 0.95rem;
    }

    /* Step indicator */
    .step-container {
        display: flex;
        justify-content: center;
        gap: 0;
        margin-bottom: 2rem;
        padding: 1rem 0;
    }
    .step {
        display: flex;
        align-items: center;
        padding: 0.5rem 1rem;
        color: #666;
        font-size: 0.9rem;
    }
    .step.active {
        color: #1E4488;
        font-weight: 600;
    }
    .step.completed {
        color: #28a745;
    }
    .step-number {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #ddd;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 0.5rem;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .step.active .step-number {
        background: #1E4488;
        color: white;
    }
    .step.completed .step-number {
        background: #28a745;
        color: white;
    }
    .step-connector {
        width: 40px;
        height: 2px;
        background: #ddd;
        margin: 0 0.5rem;
    }
    .step.completed + .step-connector,
    .step-connector.completed {
        background: #28a745;
    }

    /* Card styling */
    .info-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .info-card h4 {
        color: #1E4488;
        margin-top: 0;
        margin-bottom: 1rem;
        font-size: 1rem;
        border-bottom: 2px solid #F78E28;
        padding-bottom: 0.5rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Better button styling */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
    }
    .stButton > button[kind="primary"] {
        background-color: #1E4488;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #2a5298;
        border-color: #2a5298;
    }

    /* Cleaner metrics */
    [data-testid="metric-container"] {
        background: #F5F5FC;
        padding: 0.75rem;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

TEMPLATE_PATH = Path(__file__).parent / "templates" / "rfi_template.xlsx"
GENERATED_DIR = Path(__file__).parent / "generated"
GENERATED_DIR.mkdir(exist_ok=True)


def find_saved_files(company_name: str) -> list[Path]:
    """Find previously generated Excel files for a company, newest first."""
    safe_name = company_name.replace(" ", "_")
    files = sorted(GENERATED_DIR.glob(f"Onboarding_{safe_name}_*.xlsx"), reverse=True)
    return files


# ── Step indicator component ──────────────────────────────────────────
def render_step_indicator(current_step: str):
    steps = [
        ("search", "Search"),
        ("gather", "Gather Data"),
        ("extracting", "Extract"),
        ("review", "Review & Export")
    ]
    step_order = [s[0] for s in steps]
    current_idx = step_order.index(current_step) if current_step in step_order else 0

    html = '<div class="step-container">'
    for i, (step_key, step_label) in enumerate(steps):
        if i < current_idx:
            cls = "step completed"
        elif i == current_idx:
            cls = "step active"
        else:
            cls = "step"

        html += f'<div class="{cls}"><span class="step-number">{i+1}</span>{step_label}</div>'
        if i < len(steps) - 1:
            connector_cls = "step-connector completed" if i < current_idx else "step-connector"
            html += f'<div class="{connector_cls}"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Session state init ───────────────────────────────────────────────
def init_state():
    defaults = {
        "step": "search",           # search → review_sources → extracting → review → done
        "selected_deal": None,
        "deal_context": None,       # HubSpot company/contacts/notes
        "transcripts": None,        # None = not searched yet, [] = searched but none found
        "selected_transcripts": [], # User-selected transcripts to use
        "additional_text": "",      # Pasted URLs/content
        "uploaded_files": [],
        "extracted_answers": [],    # Final merged answers
        "excel_stats": None,
        # Manual project details (filled before processing)
        "manual_account_team": "",
        "manual_number_of_users": "",
        "manual_number_of_devices": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ── Config ───────────────────────────────────────────────────────────
@st.cache_resource
def get_config():
    return Config.from_env()


@st.cache_resource
def get_hubspot():
    return HubSpotClient(get_config().hubspot_api_key)


@st.cache_resource
def get_fireflies():
    return FirefliesClient(get_config().fireflies_api_key)


@st.cache_resource
def get_extractor():
    return RFIExtractor(get_config().anthropic_api_key)


# ── Header ───────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🔔 Onboarding Form Filler</h1>
    <p>Automatically fill onboarding forms from HubSpot deals and Fireflies transcripts</p>
</div>
""", unsafe_allow_html=True)

# Show step indicator
render_step_indicator(st.session_state["step"])


# ── Step 1: Search & Select Deal ─────────────────────────────────────
def step_search():
    st.subheader("🔍 Search for a Deal")

    # Use form to enable Enter key submission
    with st.form(key="search_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Search HubSpot deals by company name", placeholder="e.g. R&R Brands")
        with col2:
            search_clicked = st.form_submit_button("🔍 Search", use_container_width=True)

    if search_clicked and query:
        with st.spinner("Searching HubSpot..."):
            hs = get_hubspot()
            deals = hs.search_deals(query)
            if deals:
                st.session_state["search_results"] = deals
            else:
                st.warning("No deals found. Try a different search term.")

    # Display search results
    if "search_results" in st.session_state and st.session_state["search_results"]:
        st.subheader("Select a deal:")
        for deal in st.session_state["search_results"]:
            saved = find_saved_files(deal.name)
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{deal.name}**")
            with col2:
                st.write(f"Stage: {deal.stage}")
            with col3:
                st.write(f"${deal.amount}" if deal.amount else "—")
            with col4:
                if st.button("Select", key=f"select_{deal.id}"):
                    # Clear old deal data when selecting a new deal
                    st.session_state["selected_deal"] = deal
                    st.session_state["deal_context"] = None
                    st.session_state["transcripts"] = None
                    st.session_state["extracted_answers"] = []
                    st.session_state["step"] = "gather"
                    st.rerun()

            # Show saved files for this deal
            if saved:
                latest = saved[0]
                mod_time = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%b %d, %Y at %I:%M %p")
                with st.container():
                    st.info(f"📄 **Saved form available** — generated {mod_time}")
                    dl_cols = st.columns([2, 1, 3])
                    with dl_cols[0]:
                        with open(latest, "rb") as f:
                            st.download_button(
                                "⬇️ Download Latest",
                                data=f.read(),
                                file_name=latest.name,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_saved_{deal.id}",
                            )
                    if len(saved) > 1:
                        with dl_cols[1]:
                            st.caption(f"{len(saved)} versions saved")


# ── Step 2: Gather sources ───────────────────────────────────────────
def step_gather():
    deal = st.session_state["selected_deal"]
    st.header(f"2. Gathering Data for: {deal.name}")

    # Pull HubSpot context
    if not st.session_state["deal_context"]:
        with st.spinner("Pulling company data from HubSpot..."):
            hs = get_hubspot()
            context = hs.get_deal_context(deal.id)
            st.session_state["deal_context"] = context

    context = st.session_state["deal_context"]
    company = context.get("company")
    contacts = context.get("contacts", [])
    notes = context.get("notes", [])
    domain = context.get("client_domain", "")

    # Show what we found in HubSpot
    with st.expander("📊 HubSpot Data", expanded=True):
        if company:
            cols = st.columns(4)
            cols[0].metric("Company", company.name)
            cols[1].metric("Location", f"{company.city or ''}, {company.state or ''}")
            cols[2].metric("Employees", company.employee_count or "—")
            cols[3].metric("Domain", domain or "—")

        if contacts:
            st.write("**Contacts:**")
            for c in contacts:
                st.write(f"- {c.first_name} {c.last_name} — {c.email} ({c.job_title or 'N/A'})")

        if notes:
            st.write(f"**Notes:** {len(notes)} found")

    # Search Fireflies (only if not already searched)
    if st.session_state["transcripts"] is None and domain:
        with st.spinner(f"Searching Fireflies for *@{domain} participants..."):
            ff = get_fireflies()
            contact_emails = [c.email for c in contacts if c.email and domain in c.email]
            transcripts = ff.get_transcripts_for_domain(domain, contact_emails)
            st.session_state["transcripts"] = transcripts

    transcripts = st.session_state["transcripts"] or []

    with st.expander(f"🎙️ Fireflies Transcripts ({len(transcripts)} found)", expanded=True):
        if transcripts:
            for i, t in enumerate(transcripts):
                # Handle date - could be string, int timestamp, or None
                if t.date:
                    date_str = str(t.date)[:10] if isinstance(t.date, str) else "Recent"
                else:
                    date_str = "N/A"
                checked = st.checkbox(
                    f"{t.title} — {date_str} ({t.word_count:,} words)",
                    value=True,
                    key=f"transcript_{i}",
                )
            st.info(f"Total words across all transcripts: {sum(t.word_count for t in transcripts):,}")
        else:
            st.warning("No transcripts found. You can still add content below.")

    # Additional content
    st.subheader("Additional Sources (optional)")
    additional_text = st.text_area(
        "Paste any URLs or additional text content",
        placeholder="Paste Fireflies links, meeting notes, or any other relevant text...",
        height=150,
    )
    uploaded = st.file_uploader(
        "Upload documents (Word, text, PDF)",
        accept_multiple_files=True,
        type=["txt", "docx", "pdf", "md"],
    )

    st.session_state["additional_text"] = additional_text
    st.session_state["uploaded_files"] = uploaded or []

    # ── Manual Project Details (required before processing) ──────────
    st.divider()
    st.subheader("Project Details")
    st.caption("These fields are filled by the person running the onboarding form.")

    detail_cols = st.columns(3)
    with detail_cols[0]:
        account_team = st.text_input(
            "Who is the Account Team?",
            value=st.session_state["manual_account_team"],
            placeholder="e.g. John Smith (AE), Jane Doe (TA)",
        )
        st.session_state["manual_account_team"] = account_team
    with detail_cols[1]:
        num_users = st.text_input(
            "Number of Users",
            value=st.session_state["manual_number_of_users"],
            placeholder="e.g. 45",
        )
        st.session_state["manual_number_of_users"] = num_users
    with detail_cols[2]:
        num_devices = st.text_input(
            "Number of Machines",
            value=st.session_state["manual_number_of_devices"],
            placeholder="e.g. 50",
        )
        st.session_state["manual_number_of_devices"] = num_devices

    # Proceed
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("⬅️ Back to Search"):
            st.session_state["step"] = "search"
            # Don't clear cached data - keeps things fast if user goes forward again
            st.rerun()
    with col2:
        if st.button("🚀 Generate Form", type="primary", use_container_width=True):
            st.session_state["step"] = "extracting"
            st.rerun()


# ── Step 3: Extract ──────────────────────────────────────────────────
def step_extracting():
    deal = st.session_state["selected_deal"]
    st.header(f"3. Extracting Data for: {deal.name}")

    context = st.session_state["deal_context"]
    company = context.get("company")
    transcripts = st.session_state["transcripts"]

    # Build source list
    sources: list[tuple[str, str]] = []

    # Add transcripts
    progress = st.progress(0, "Preparing sources...")
    for i, t in enumerate(transcripts):
        date_str = str(t.date)[:10] if isinstance(t.date, str) else "Recent" if t.date else "N/A"
        sources.append((f"Transcript: {t.title} ({date_str})", t.full_text))
        progress.progress((i + 1) / max(len(transcripts), 1), f"Loaded transcript {i+1}/{len(transcripts)}")

    # Add HubSpot notes
    notes = context.get("notes", [])
    if notes:
        notes_text = "\n\n---\n\n".join(
            f"[{n.get('timestamp', 'N/A')}]\n{n.get('body', '')}" for n in notes
        )
        sources.append(("HubSpot Notes", notes_text))

    # Add pasted text
    if st.session_state.get("additional_text", "").strip():
        sources.append(("User-provided text", st.session_state["additional_text"]))

    # Add uploaded files
    for f in st.session_state.get("uploaded_files", []):
        content = f.read().decode("utf-8", errors="ignore")
        sources.append((f"Uploaded: {f.name}", content))

    if not sources:
        st.error("No sources available. Go back and add some content.")
        if st.button("⬅️ Back"):
            st.session_state["step"] = "gather"
            st.rerun()
        return

    # Run extraction
    st.info(f"Extracting from {len(sources)} sources with {len(RFI_FIELDS)} fields...")
    extractor = get_extractor()

    with st.spinner("Claude is reading transcripts and extracting answers... (this may take 1-2 minutes)"):
        all_answers = extractor.extract_from_multiple_sources(sources)

    # Build HubSpot structured data for merge
    contacts = context.get("contacts", [])
    hubspot_data = {}
    if company:
        # Primary contact (first contact with an email)
        primary_contact = next((c for c in contacts if c.email), None)

        hubspot_data = {
            "name": company.name,
            "city": f"{company.city or ''}, {company.state or ''}".strip(", "),
            "numberofemployees": company.employee_count,
            "domain": company.domain,
            "industry": company.industry,
            # Contact fields
            "main_contact_name": f"{primary_contact.first_name} {primary_contact.last_name}".strip() if primary_contact else None,
            "main_contact_email": primary_contact.email if primary_contact else None,
            "main_contact_phone": primary_contact.phone if primary_contact else None,
            # Deal-level fields
            "deal_owner": context.get("deal_owner"),
            "closedate": context.get("close_date"),
        }

    # Merge answers
    merged = merge_answers(all_answers, hubspot_data)

    # Override with manual project details (highest priority)
    manual_overrides = {
        "bellwether_team": st.session_state.get("manual_account_team", ""),
        "number_of_users": st.session_state.get("manual_number_of_users", ""),
        "number_of_devices": st.session_state.get("manual_number_of_devices", ""),
    }
    for answer in merged:
        override_val = manual_overrides.get(answer.field_key, "")
        if override_val.strip():
            answer.answer = override_val.strip()
            answer.confidence = Confidence.HIGH
            answer.source = "Manual entry"
            answer.evidence = ""

    st.session_state["extracted_answers"] = merged
    st.session_state["step"] = "review"
    st.rerun()


# ── Step 4: Review & Download ────────────────────────────────────────
def step_review():
    deal = st.session_state["selected_deal"]
    answers = st.session_state["extracted_answers"]
    context = st.session_state["deal_context"]
    company = context.get("company")
    company_name = company.name if company else deal.name

    st.header(f"4. Review: {company_name}")

    # Stats
    total = len(answers)
    filled = sum(1 for a in answers if a.confidence != Confidence.MISSING)
    high = sum(1 for a in answers if a.confidence == Confidence.HIGH)
    medium = sum(1 for a in answers if a.confidence == Confidence.MEDIUM)
    low = sum(1 for a in answers if a.confidence == Confidence.LOW)
    missing = sum(1 for a in answers if a.confidence == Confidence.MISSING)

    cols = st.columns(5)
    cols[0].metric("Total Fields", total)
    cols[1].metric("Filled", filled, f"{round(filled/total*100)}%")
    cols[2].metric("High Confidence", high)
    cols[3].metric("Medium Confidence", medium)
    cols[4].metric("Missing", missing)

    st.divider()

    # Editable review table
    st.subheader("Review Extracted Answers")
    st.caption("Edit any answers before generating the final Excel.")

    # Group by category
    from schema.rfi_fields import get_fields_by_category, Category
    field_map = {f.key: f for f in RFI_FIELDS}
    answer_map = {a.field_key: a for a in answers}

    for category in Category:
        category_answers = [a for a in answers if field_map.get(a.field_key, None) and field_map[a.field_key].category == category]
        if not category_answers:
            continue

        with st.expander(f"**{category.value}** ({sum(1 for a in category_answers if a.confidence != Confidence.MISSING)}/{len(category_answers)} filled)"):
            for a in category_answers:
                conf_emoji = {
                    Confidence.HIGH: "🟢",
                    Confidence.MEDIUM: "🟡",
                    Confidence.LOW: "🔴",
                    Confidence.MISSING: "⬜",
                }[a.confidence]

                st.write(f"{conf_emoji} **{a.question}**")
                new_val = st.text_area(
                    f"Answer",
                    value=a.answer or "",
                    key=f"edit_{a.field_key}",
                    height=68,
                    label_visibility="collapsed",
                )
                # Update answer if edited
                if new_val != (a.answer or ""):
                    a.answer = new_val
                    if new_val.strip():
                        a.confidence = Confidence.HIGH
                        a.source = "Manual edit"

                if a.source:
                    st.caption(f"Source: {a.source}")
                st.write("")  # spacing

    st.divider()

    # Generate Excel
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state["step"] = "gather"
            st.rerun()
    with col2:
        if st.button("📥 Generate & Download Excel", type="primary", use_container_width=True):
            with st.spinner("Generating Excel..."):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"Onboarding_{company_name.replace(' ', '_')}_{timestamp}.xlsx"
                output_path = GENERATED_DIR / filename

                stats = generate_rfi_excel(
                    answers=answers,
                    template_path=TEMPLATE_PATH,
                    output_path=output_path,
                    company_name=company_name,
                )
                st.session_state["excel_stats"] = stats

                with open(output_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download {filename}",
                        data=f.read(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                st.success(f"Form generated and saved: {stats['completion_pct']}% complete ({stats['filled']}/{stats['total_fields']} fields)")


# ── Router ───────────────────────────────────────────────────────────
step = st.session_state["step"]
if step == "search":
    step_search()
elif step == "gather":
    step_gather()
elif step == "extracting":
    step_extracting()
elif step == "review":
    step_review()


# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Status")
    steps = ["search", "gather", "extracting", "review"]
    labels = ["🔍 Search Deal", "📂 Gather Sources", "🤖 Extracting", "📋 Review & Download"]
    current = steps.index(step) if step in steps else 0
    for i, label in enumerate(labels):
        if i < current:
            st.write(f"✅ {label}")
        elif i == current:
            st.write(f"➡️ **{label}**")
        else:
            st.write(f"⬜ {label}")

    st.divider()
    st.caption("Onboarding Form Filler v1.0")
    st.caption(f"Fields in schema: {len(RFI_FIELDS)}")
    if st.session_state.get("selected_deal"):
        st.caption(f"Deal: {st.session_state['selected_deal'].name}")
