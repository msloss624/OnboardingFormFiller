"""
RFI AutoFiller — Streamlit App
Search a HubSpot deal, pull transcripts, extract answers, generate filled RFI.
"""
import os
import sys
import json
import tempfile
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
    page_title="RFI AutoFiller",
    page_icon="📋",
    layout="wide",
)

TEMPLATE_PATH = Path(__file__).parent / "templates" / "rfi_template.xlsx"


# ── Session state init ───────────────────────────────────────────────
def init_state():
    defaults = {
        "step": "search",           # search → review_sources → extracting → review → done
        "selected_deal": None,
        "deal_context": None,       # HubSpot company/contacts/notes
        "transcripts": [],          # Fireflies transcripts found
        "selected_transcripts": [], # User-selected transcripts to use
        "additional_text": "",      # Pasted URLs/content
        "uploaded_files": [],
        "extracted_answers": [],    # Final merged answers
        "excel_stats": None,
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
st.title("📋 RFI AutoFiller")
st.caption("Search a deal → pull transcripts → extract answers → download filled RFI")
st.divider()


# ── Step 1: Search & Select Deal ─────────────────────────────────────
def step_search():
    st.header("1. Select a Deal")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Search HubSpot deals by company name", placeholder="e.g. R&R Brands")
    with col2:
        search_clicked = st.button("🔍 Search", use_container_width=True)

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
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{deal.name}**")
            with col2:
                st.write(f"Stage: {deal.stage}")
            with col3:
                st.write(f"${deal.amount}" if deal.amount else "—")
            with col4:
                if st.button("Select", key=f"select_{deal.id}"):
                    st.session_state["selected_deal"] = deal
                    st.session_state["step"] = "gather"
                    st.rerun()


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

    # Search Fireflies
    if not st.session_state["transcripts"] and domain:
        with st.spinner(f"Searching Fireflies for *@{domain} participants..."):
            ff = get_fireflies()
            contact_emails = [c.email for c in contacts if c.email and domain in c.email]
            transcripts = ff.get_transcripts_for_domain(domain, contact_emails)
            st.session_state["transcripts"] = transcripts

    transcripts = st.session_state["transcripts"]

    with st.expander(f"🎙️ Fireflies Transcripts ({len(transcripts)} found)", expanded=True):
        if transcripts:
            for i, t in enumerate(transcripts):
                checked = st.checkbox(
                    f"{t.title} — {t.date[:10] if t.date else 'N/A'} ({t.word_count:,} words)",
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

    # Proceed
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state["step"] = "search"
            st.session_state["deal_context"] = None
            st.session_state["transcripts"] = []
            st.rerun()
    with col2:
        if st.button("🚀 Generate RFI", type="primary", use_container_width=True):
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
        sources.append((f"Transcript: {t.title} ({t.date[:10] if t.date else 'N/A'})", t.full_text))
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
    st.info(f"Extracting from {len(sources)} sources with {len(RFI_FIELDS)} RFI fields...")
    extractor = get_extractor()

    with st.spinner("Claude is reading transcripts and extracting answers... (this may take 1-2 minutes)"):
        all_answers = extractor.extract_from_multiple_sources(sources)

    # Build HubSpot structured data for merge
    hubspot_data = {}
    if company:
        hubspot_data = {
            "name": company.name,
            "city": f"{company.city or ''}, {company.state or ''}".strip(", "),
            "numberofemployees": company.employee_count,
            "domain": company.domain,
            "industry": company.industry,
        }

    # Merge answers
    merged = merge_answers(all_answers, hubspot_data)
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
                filename = f"RFI_{company_name.replace(' ', '_')}_{timestamp}.xlsx"
                output_path = Path(tempfile.gettempdir()) / filename

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

                st.success(f"RFI generated: {stats['completion_pct']}% complete ({stats['filled']}/{stats['total_fields']} fields)")


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
    st.caption("RFI AutoFiller v1.0")
    st.caption(f"Fields in schema: {len(RFI_FIELDS)}")
    if st.session_state.get("selected_deal"):
        st.caption(f"Deal: {st.session_state['selected_deal'].name}")
