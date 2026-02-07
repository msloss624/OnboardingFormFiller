"""
Transcript routes — search Fireflies transcripts by domain/emails.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.config import get_config
from clients.fireflies_client import FirefliesClient

router = APIRouter()


def _get_fireflies() -> FirefliesClient:
    return FirefliesClient(get_config().fireflies_api_key)


@router.get("")
async def search_transcripts(
    domain: str = Query(..., min_length=1),
    emails: str = Query(""),  # comma-separated emails
):
    ff = _get_fireflies()
    contact_emails = [e.strip() for e in emails.split(",") if e.strip()] if emails else []
    transcripts = ff.get_transcripts_for_domain(domain, contact_emails)
    return [
        {
            "id": t.id,
            "title": t.title,
            "date": t.date,
            "speakers": t.speakers,
            "word_count": t.word_count,
            "summary": t.summary,
        }
        for t in transcripts
    ]
