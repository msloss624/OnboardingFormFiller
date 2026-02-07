"""
Export routes — download Excel (from storage or generated on-the-fly), list run history.
"""
from __future__ import annotations
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import Run
from backend.storage import download_excel as storage_download, upload_excel
from extraction.extractor import ExtractedAnswer
from output.excel_generator import generate_rfi_excel
from schema.rfi_fields import Confidence

router = APIRouter()

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "rfi_template.xlsx"


def _answers_from_json(answers_json: str) -> list[ExtractedAnswer]:
    """Convert stored JSON answers back to ExtractedAnswer objects."""
    raw = json.loads(answers_json)
    return [
        ExtractedAnswer(
            field_key=a["field_key"],
            question=a["question"],
            answer=a.get("answer"),
            confidence=Confidence(a.get("confidence", "missing")),
            source=a.get("source", ""),
            evidence=a.get("evidence", ""),
            row=a["row"],
        )
        for a in raw
    ]


@router.get("/{run_id}/excel")
async def download_excel(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    if not run.answers_json:
        raise HTTPException(400, "Run has no answers yet")

    company_name = run.company_name or run.deal_name
    safe_name = company_name.replace(" ", "_")

    # Try to serve pre-generated Excel from storage
    if run.excel_blob_path:
        file_bytes = storage_download(run.excel_blob_path)
        if file_bytes:
            filename = run.excel_blob_path.rsplit("/", 1)[-1]
            return Response(
                content=file_bytes,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )

    # Fallback: generate fresh, upload to storage, update run
    answers = _answers_from_json(run.answers_json)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    filename = f"Onboarding_{safe_name}_{timestamp}.xlsx"
    blob_path = f"runs/{run_id}/{filename}"

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp:
        tmp_path = Path(tmp.name)
        generate_rfi_excel(
            answers=answers,
            template_path=TEMPLATE_PATH,
            output_path=tmp_path,
            company_name=company_name,
        )
        file_bytes = tmp_path.read_bytes()

    stored_path = upload_excel(blob_path, file_bytes)
    run.excel_blob_path = stored_path
    await db.commit()

    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("")
async def list_runs(
    deal_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Run).order_by(Run.created_at.desc())
    if deal_id:
        query = query.where(Run.deal_id == deal_id)

    result = await db.execute(query)
    runs = result.scalars().all()

    return [
        {
            "id": r.id,
            "deal_id": r.deal_id,
            "deal_name": r.deal_name,
            "company_name": r.company_name,
            "status": r.status,
            "stats": json.loads(r.stats_json) if r.stats_json else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]
