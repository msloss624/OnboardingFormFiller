"""
Email routes — preview and send onboarding summary to the account team.
"""
from __future__ import annotations
import asyncio
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.auth import get_current_user
from backend.config import get_config
from backend.database import get_db
from backend.models import Run, User
from backend.storage import download_excel as storage_download, upload_excel
from backend.services.graph_email import build_email_body, send_email
from clients.hubspot_client import HubSpotClient
from extraction.extractor import ExtractedAnswer
from output.excel_generator import generate_rfi_excel
from schema.rfi_fields import Confidence

router = APIRouter()

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "rfi_template.xlsx"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB

logger = logging.getLogger(__name__)


def _get_answer(answers: list[dict], field_key: str) -> str:
    """Extract an answer value by field key, returning empty string if missing."""
    for a in answers:
        if a.get("field_key") == field_key:
            return a.get("answer") or ""
    return ""


def _build_fields(answers: list[dict], run: Run, deal_amount: str = "") -> dict:
    """Build the email field dict from answers and run data."""
    contact_parts = []
    for key in ("main_contact_name", "main_contact_email", "main_contact_phone"):
        val = _get_answer(answers, key)
        if val:
            contact_parts.append(val)

    client_name = _get_answer(answers, "company_name") or run.company_name or run.deal_name
    return {
        "client_name": client_name,
        "company_description": _get_answer(answers, "industry_vertical"),
        "contract_amount": f"${deal_amount}" if deal_amount else "",
        "account_team": _get_answer(answers, "bellwether_team"),
        "number_of_users": _get_answer(answers, "number_of_users"),
        "number_of_devices": _get_answer(answers, "number_of_devices"),
        "pain_points": _get_answer(answers, "pain_points"),
        "service_scope": _get_answer(answers, "contract_type"),
        "go_live_date": _get_answer(answers, "desired_go_live"),
        "primary_contact": " | ".join(contact_parts) if contact_parts else "",
    }


def _get_excel_bytes(run: Run) -> tuple[bytes, str]:
    """Get Excel file bytes and filename, from storage or by generating fresh."""
    company_name = run.company_name or run.deal_name
    safe_name = company_name.replace(" ", "_")

    if run.excel_blob_path:
        file_bytes = storage_download(run.excel_blob_path)
        if file_bytes:
            filename = run.excel_blob_path.rsplit("/", 1)[-1]
            return file_bytes, filename

    answers = json.loads(run.answers_json)
    extracted = [
        ExtractedAnswer(
            field_key=a["field_key"],
            question=a["question"],
            answer=a.get("answer"),
            confidence=Confidence(a.get("confidence", "missing")),
            source=a.get("source", ""),
            evidence=a.get("evidence", ""),
            row=a["row"],
        )
        for a in answers
    ]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"Onboarding_{safe_name}_{timestamp}.xlsx"

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
        tmp_path = Path(tmp.name)
        generate_rfi_excel(
            answers=extracted,
            template_path=TEMPLATE_PATH,
            output_path=tmp_path,
            company_name=company_name,
        )
        file_bytes = tmp_path.read_bytes()

    blob_path = f"runs/{run.id}/{filename}"
    stored_path = upload_excel(blob_path, file_bytes)
    run.excel_blob_path = stored_path

    return file_bytes, filename


def _validate_upload(file: UploadFile, contents: bytes) -> None:
    """Validate file extension and size."""
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, "File too large (max 20 MB)")


@router.get("/{run_id}/email-preview")
async def get_email_preview(
    run_id: str,
    _user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return pre-populated email fields for the send page."""
    config = get_config()

    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    if not run.answers_json:
        raise HTTPException(400, "Run has no answers")

    answers = json.loads(run.answers_json)

    # Fetch deal data from HubSpot
    deal_amount = ""
    deal_owner_email = None
    try:
        hs = HubSpotClient(config.hubspot_api_key)
        deal_props = hs.get_deal_properties(run.deal_id)
        deal_amount = deal_props.get("amount") or ""
        owner_id = deal_props.get("hubspot_owner_id")
        if owner_id:
            deal_owner_email = hs.get_owner_email(owner_id)
        hs.close()
    except Exception as e:
        logger.warning("Failed to fetch HubSpot deal data: %s", e)

    fields = _build_fields(answers, run, deal_amount)

    # Build recipient list (deduplicated)
    recipients = []
    if config.onboarding_team_email:
        recipients.append(config.onboarding_team_email)
    if deal_owner_email and deal_owner_email.lower() not in [r.lower() for r in recipients]:
        recipients.append(deal_owner_email)

    return {
        "subject": f"New Onboarding: {fields['client_name']}",
        "fields": fields,
        "recipients": recipients,
        "email_sent_at": run.email_sent_at.isoformat() if run.email_sent_at else None,
    }


@router.post("/{run_id}/send-email")
async def send_to_account_team(
    run_id: str,
    subject: str = Form(...),
    recipients: str = Form(...),  # comma-separated emails
    fields_json: str = Form(...),  # JSON string of email body fields
    sow: Optional[UploadFile] = File(None),
    msa: Optional[UploadFile] = File(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send onboarding summary email with user-edited content."""
    # Parse inputs
    to_emails = [e.strip() for e in recipients.split(",") if e.strip()]
    if not to_emails:
        raise HTTPException(400, "At least one recipient is required")

    try:
        fields = json.loads(fields_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid fields JSON")

    # Load the run
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status != "completed":
        raise HTTPException(400, "Can only send email for completed runs")
    if not run.answers_json:
        raise HTTPException(400, "Run has no answers")

    # Build HTML from the (possibly edited) fields
    html_body = build_email_body(fields)

    # Build attachments
    attachments = []

    # Excel (auto-attached)
    excel_bytes, excel_filename = await asyncio.to_thread(_get_excel_bytes, run)
    attachments.append({
        "filename": excel_filename,
        "content_bytes": excel_bytes,
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    })

    # SOW (optional)
    if sow and sow.filename:
        sow_contents = await sow.read()
        _validate_upload(sow, sow_contents)
        attachments.append({
            "filename": sow.filename,
            "content_bytes": sow_contents,
            "content_type": sow.content_type or "application/octet-stream",
        })

    # MSA (optional)
    if msa and msa.filename:
        msa_contents = await msa.read()
        _validate_upload(msa, msa_contents)
        attachments.append({
            "filename": msa.filename,
            "content_bytes": msa_contents,
            "content_type": msa.content_type or "application/octet-stream",
        })

    # Send
    result_data = await asyncio.to_thread(send_email, to_emails, subject, html_body, attachments)

    # Track sent status
    run.email_sent_at = datetime.now(timezone.utc)
    run.email_sent_by = user.email
    await db.commit()

    return {
        "status": result_data.get("status", "sent"),
        "email_sent_at": run.email_sent_at.isoformat(),
        "recipients": to_emails,
    }
