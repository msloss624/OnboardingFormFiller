"""
Auth routes — user info endpoint.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.models import User

router = APIRouter()


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
    }
