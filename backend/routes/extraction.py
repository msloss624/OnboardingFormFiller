"""
Extraction routes — start runs, poll status, save edited answers, retry fields.
"""
from __future__ import annotations
import asyncio
import json
import threading
from typing import Optional

import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import User, Run
from backend.auth import get_current_user
from backend.services.extraction_service import run_extraction, retry_single_field

router = APIRouter()


class RunRequest(BaseModel):
    deal_id: str
    deal_name: str
    transcript_ids: list[str] = []
    additional_text: str = ""
    manual_overrides: dict[str, str] = {}
    baseline_run_id: Optional[str] = None


class AnswerUpdate(BaseModel):
    answers: list[dict]  # [{field_key, answer, confidence, source, evidence}]


class RetryFieldRequest(BaseModel):
    field_key: str
    prompt_hint: str = ""


@router.post("")
async def create_run(
    req: RunRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    run = Run(
        deal_id=req.deal_id,
        deal_name=req.deal_name,
        user_id=user.id,
        status="pending",
        transcript_ids=json.dumps(req.transcript_ids) if req.transcript_ids else None,
        baseline_run_id=req.baseline_run_id,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Launch background extraction
    thread = threading.Thread(
        target=run_extraction,
        args=(run.id, req.deal_id, req.transcript_ids, req.additional_text,
              req.manual_overrides, req.baseline_run_id),
        daemon=True,
    )
    thread.start()

    return {"id": run.id, "status": run.status}


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


@router.post("/upload")
async def upload_file(file: UploadFile, _user=Depends(get_current_user)):
    """Extract text from an uploaded PDF or Word document."""
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    contents = await file.read()

    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(contents))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext in (".docx", ".doc"):
        from docx import Document

        doc = Document(io.BytesIO(contents))
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        raise HTTPException(400, "Unsupported file type")

    return {"filename": filename, "text": text.strip()}


@router.get("/{run_id}")
async def get_run(run_id: str, _user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")

    return {
        "id": run.id,
        "deal_id": run.deal_id,
        "deal_name": run.deal_name,
        "company_name": run.company_name,
        "status": run.status,
        "answers": json.loads(run.answers_json) if run.answers_json else None,
        "sources_used": json.loads(run.sources_used) if run.sources_used else None,
        "stats": json.loads(run.stats_json) if run.stats_json else None,
        "excel_blob_path": run.excel_blob_path,
        "baseline_run_id": run.baseline_run_id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
    }


@router.put("/{run_id}/answers")
async def update_answers(
    run_id: str,
    body: AnswerUpdate,
    _user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")

    run.answers_json = json.dumps(body.answers)
    await db.commit()
    return {"status": "saved"}


@router.delete("/{run_id}")
async def delete_run(run_id: str, _user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    await db.delete(run)
    await db.commit()
    return {"status": "deleted"}


@router.post("/{run_id}/retry-field")
async def retry_field(
    run_id: str,
    body: RetryFieldRequest,
    _user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-extract a single field with a more aggressive prompt."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    if run.status != "completed":
        raise HTTPException(400, "Can only retry fields on completed runs")
    if not run.answers_json:
        raise HTTPException(400, "Run has no answers to retry")

    deal_id = run.deal_id
    transcript_ids = json.loads(run.transcript_ids) if run.transcript_ids else []

    # Run sync Claude call in a thread
    result_data = await asyncio.to_thread(
        retry_single_field,
        run.id, deal_id, transcript_ids,
        body.field_key, body.prompt_hint,
        run.answers_json,
    )

    # Update the run in DB
    run.answers_json = result_data["answers_json"]
    run.stats_json = result_data["stats_json"]
    await db.commit()

    return result_data["updated_answer"]
