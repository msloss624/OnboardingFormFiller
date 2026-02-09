"""
Deal routes — search HubSpot deals, get deal context.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.auth import get_current_user
from backend.config import get_config
from clients.hubspot_client import HubSpotClient

router = APIRouter()


def _get_hubspot() -> HubSpotClient:
    return HubSpotClient(get_config().hubspot_api_key)


@router.get("/search")
async def search_deals(q: str = Query(..., min_length=1), _user=Depends(get_current_user)):
    hs = _get_hubspot()
    deals = hs.search_deals(q)
    return [
        {
            "id": d.id,
            "name": d.name,
            "stage": d.stage,
            "amount": d.amount,
            "close_date": d.close_date,
        }
        for d in deals
    ]


@router.get("/{deal_id}/context")
async def get_deal_context(deal_id: str, _user=Depends(get_current_user)):
    hs = _get_hubspot()
    ctx = hs.get_deal_context(deal_id)
    if "error" in ctx:
        return {"error": ctx["error"]}

    company = ctx.get("company")
    contacts = ctx.get("contacts", [])
    notes = ctx.get("notes", [])

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "domain": company.domain,
            "city": company.city,
            "state": company.state,
            "industry": company.industry,
            "employee_count": company.employee_count,
        } if company else None,
        "contacts": [
            {
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "phone": c.phone,
                "job_title": c.job_title,
            }
            for c in contacts
        ],
        "notes": notes,
        "client_domain": ctx.get("client_domain"),
        "deal_owner": ctx.get("deal_owner"),
        "close_date": ctx.get("close_date"),
    }
