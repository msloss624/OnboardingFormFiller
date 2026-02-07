"""
Background extraction orchestration.
Runs in a thread: build sources → extract → merge → baseline merge → manual overrides → save to DB.
"""
from __future__ import annotations
import json
import logging
import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_config
from backend.database import get_session_factory
from backend.models import Run
from clients.hubspot_client import HubSpotClient
from clients.fireflies_client import FirefliesClient
from extraction.extractor import RFIExtractor, ExtractedAnswer, merge_answers
from output.excel_generator import generate_rfi_excel
from backend.storage import upload_excel
from schema.rfi_fields import RFI_FIELDS, Confidence

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "rfi_template.xlsx"

logger = logging.getLogger(__name__)


def _format_date(value: str | None) -> str | None:
    """Format a date string (e.g. '2026-03-15T00:00:00.000Z') to 'March 15, 2026'."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except (ValueError, AttributeError):
        return value


def _answer_to_dict(a: ExtractedAnswer) -> dict:
    return {
        "field_key": a.field_key,
        "question": a.question,
        "answer": a.answer,
        "confidence": a.confidence.value,
        "source": a.source,
        "evidence": a.evidence,
        "row": a.row,
    }


def run_extraction(
    run_id: str,
    deal_id: str,
    transcript_ids: list[str],
    additional_text: str,
    manual_overrides: dict[str, str],
    baseline_run_id: str | None,
):
    """Entry point for background thread. Creates its own event loop for async DB access."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _do_extraction(run_id, deal_id, transcript_ids, additional_text,
                           manual_overrides, baseline_run_id)
        )
    finally:
        loop.close()


async def _update_run(session: AsyncSession, run_id: str, **kwargs):
    result = await session.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one()
    for k, v in kwargs.items():
        setattr(run, k, v)
    await session.commit()


async def _do_extraction(
    run_id: str,
    deal_id: str,
    transcript_ids: list[str],
    additional_text: str,
    manual_overrides: dict[str, str],
    baseline_run_id: str | None,
):
    config = get_config()
    factory = get_session_factory()

    async with factory() as db:
        await _update_run(db, run_id, status="extracting")

    try:
        # 1. Get deal context from HubSpot
        hs = HubSpotClient(config.hubspot_api_key)
        context = hs.get_deal_context(deal_id)
        company = context.get("company")
        contacts = context.get("contacts", [])
        notes = context.get("notes", [])
        domain = context.get("client_domain", "")
        company_name = company.name if company else ""

        # Update company name on the run
        async with factory() as db:
            await _update_run(db, run_id, company_name=company_name)

        # 2. Fetch selected transcripts from Fireflies (in parallel)
        sources: list[tuple[str, str]] = []
        if transcript_ids:
            ff = FirefliesClient(config.fireflies_api_key)
            import concurrent.futures

            def fetch_transcript(tid: str):
                t = ff.get_full_transcript(tid)
                date_str = str(t.date)[:10] if isinstance(t.date, str) else "Recent" if t.date else "N/A"
                return (f"Transcript: {t.title} ({date_str})", t.full_text)

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(transcript_ids), 5)) as executor:
                futures = {executor.submit(fetch_transcript, tid): tid for tid in transcript_ids}
                for future in concurrent.futures.as_completed(futures):
                    tid = futures[future]
                    try:
                        sources.append(future.result())
                    except Exception as e:
                        logger.warning(f"Failed to fetch transcript {tid}: {e}")

        # 3. Add HubSpot notes
        if notes:
            notes_text = "\n\n---\n\n".join(
                f"[{n.get('timestamp', 'N/A')}]\n{n.get('body', '')}" for n in notes
            )
            sources.append(("HubSpot Notes", notes_text))

        # 4. Add user-provided text
        if additional_text and additional_text.strip():
            sources.append(("User-provided text", additional_text))

        if not sources:
            async with factory() as db:
                await _update_run(db, run_id, status="failed",
                                  error_message="No sources available for extraction")
            return

        # 5. Run extraction
        extractor = RFIExtractor(config.anthropic_api_key)
        all_answers = extractor.extract_from_multiple_sources(sources)

        # 6. Build HubSpot structured data for merge
        hubspot_data = {}
        if company:
            primary_contact = next((c for c in contacts if c.email), None)
            hubspot_data = {
                "name": company.name,
                "city": f"{company.city or ''}, {company.state or ''}".strip(", "),
                "numberofemployees": company.employee_count,
                "domain": company.domain,
                "industry": company.industry,
                "main_contact_name": (
                    f"{primary_contact.first_name} {primary_contact.last_name}".strip()
                    if primary_contact else None
                ),
                "main_contact_email": primary_contact.email if primary_contact else None,
                "main_contact_phone": primary_contact.phone if primary_contact else None,
                "deal_owner": context.get("deal_owner"),
                "closedate": _format_date(context.get("close_date")),
            }

        merged = merge_answers(all_answers, hubspot_data)

        # 6b. Confidence calibration — downgrade overconfident answers
        has_calibration_candidates = any(
            a.confidence in (Confidence.HIGH, Confidence.MEDIUM) and a.evidence and a.answer
            for a in merged
        )
        if has_calibration_candidates:
            merged = extractor.calibrate_confidence(merged)

        # 7. Merge with baseline (if continuing from a previous run)
        if baseline_run_id:
            async with factory() as db:
                result = await db.execute(select(Run).where(Run.id == baseline_run_id))
                baseline_run = result.scalar_one_or_none()
                if baseline_run and baseline_run.answers_json:
                    baseline_raw = json.loads(baseline_run.answers_json)
                    baseline_map = {
                        a["field_key"]: ExtractedAnswer(
                            field_key=a["field_key"],
                            question=a["question"],
                            answer=a.get("answer"),
                            confidence=Confidence(a.get("confidence", "missing")),
                            source=a.get("source", ""),
                            evidence=a.get("evidence", ""),
                            row=a["row"],
                        )
                        for a in baseline_raw
                    }
                    for i, answer in enumerate(merged):
                        base = baseline_map.get(answer.field_key)
                        if not base:
                            continue
                        base_has = base.confidence != Confidence.MISSING and base.answer
                        new_has = answer.confidence != Confidence.MISSING and answer.answer
                        if base_has and not new_has:
                            merged[i] = base
                        elif base_has and new_has:
                            if not (answer.confidence == Confidence.HIGH and base.confidence == Confidence.LOW):
                                merged[i] = base

        # 8. Apply manual overrides (highest priority)
        for answer in merged:
            override_val = manual_overrides.get(answer.field_key, "")
            if override_val.strip():
                answer.answer = override_val.strip()
                answer.confidence = Confidence.HIGH
                answer.source = "Manual entry"
                answer.evidence = ""

        # 9. Compute stats and save
        total = len(merged)
        filled = sum(1 for a in merged if a.confidence != Confidence.MISSING)
        source_names = sorted(set(a.source for a in merged if a.source))
        stats = {
            "total_fields": total,
            "filled": filled,
            "completion_pct": round(filled / total * 100, 1) if total else 0,
            "by_confidence": {
                c.value: sum(1 for a in merged if a.confidence == c)
                for c in Confidence
            },
        }

        answers_data = [_answer_to_dict(a) for a in merged]

        # 10. Generate Excel and upload to storage
        excel_blob_path = None
        try:
            safe_name = (company_name or "unknown").replace(" ", "_")
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
            filename = f"Onboarding_{safe_name}_{timestamp}.xlsx"
            blob_path = f"runs/{run_id}/{filename}"

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
                tmp_path = Path(tmp.name)
                generate_rfi_excel(
                    answers=merged,
                    template_path=TEMPLATE_PATH,
                    output_path=tmp_path,
                    company_name=company_name,
                )
                excel_bytes = tmp_path.read_bytes()

            excel_blob_path = upload_excel(blob_path, excel_bytes)
            logger.info(f"Excel saved: {excel_blob_path}")
        except Exception as exc:
            logger.warning(f"Excel generation failed (non-fatal): {exc}")

        async with factory() as db:
            await _update_run(
                db, run_id,
                status="completed",
                answers_json=json.dumps(answers_data),
                sources_used=json.dumps(source_names),
                stats_json=json.dumps(stats),
                excel_blob_path=excel_blob_path,
                completed_at=datetime.now(timezone.utc),
            )

        logger.info(f"Run {run_id} completed: {stats['completion_pct']}% filled")

    except Exception as e:
        logger.exception(f"Run {run_id} failed: {e}")
        async with factory() as db:
            await _update_run(
                db, run_id,
                status="failed",
                error_message=str(e),
            )


def retry_single_field(
    run_id: str,
    deal_id: str,
    transcript_ids: list[str],
    field_key: str,
    prompt_hint: str,
    answers_json: str,
) -> dict:
    """Re-extract a single field and return the updated answer dict."""
    config = get_config()

    # 1. Re-fetch sources
    sources: list[tuple[str, str]] = []

    hs = HubSpotClient(config.hubspot_api_key)
    context = hs.get_deal_context(deal_id)
    notes = context.get("notes", [])

    if transcript_ids:
        ff = FirefliesClient(config.fireflies_api_key)
        for tid in transcript_ids:
            try:
                t = ff.get_full_transcript(tid)
                date_str = str(t.date)[:10] if isinstance(t.date, str) else "Recent" if t.date else "N/A"
                sources.append((f"Transcript: {t.title} ({date_str})", t.full_text))
            except Exception as e:
                logger.warning(f"Failed to fetch transcript {tid}: {e}")

    if notes:
        notes_text = "\n\n---\n\n".join(
            f"[{n.get('timestamp', 'N/A')}]\n{n.get('body', '')}" for n in notes
        )
        sources.append(("HubSpot Notes", notes_text))

    if not sources:
        raise ValueError("No sources available for re-extraction")

    # 2. Run single-field extraction
    extractor = RFIExtractor(config.anthropic_api_key)
    result = extractor.extract_single_field(field_key, sources, prompt_hint)

    # 3. Patch into the existing answers
    existing = json.loads(answers_json)
    updated_answer = _answer_to_dict(result)

    for i, a in enumerate(existing):
        if a["field_key"] == field_key:
            existing[i] = updated_answer
            break

    # 4. Recompute stats
    total = len(existing)
    filled = sum(1 for a in existing if a.get("confidence") != "missing")
    stats = {
        "total_fields": total,
        "filled": filled,
        "completion_pct": round(filled / total * 100, 1) if total else 0,
        "by_confidence": {
            c.value: sum(1 for a in existing if a.get("confidence") == c.value)
            for c in Confidence
        },
    }

    return {
        "answers_json": json.dumps(existing),
        "stats_json": json.dumps(stats),
        "updated_answer": updated_answer,
    }
