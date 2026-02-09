"""
Azure AD JWT validation middleware.
When AZURE_AD_TENANT_ID is configured, validates Bearer tokens via Azure AD JWKS.
Otherwise falls back to a dev user (no auth required).
"""
from __future__ import annotations
import logging
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_config
from backend.database import get_db
from backend.models import User

logger = logging.getLogger(__name__)

_jwks_cache: Optional[dict] = None


def _get_jwks(tenant_id: str) -> dict:
    """Fetch and cache the Azure AD JWKS (JSON Web Key Set)."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    return _jwks_cache


def _decode_token(token: str) -> dict:
    """Validate and decode an Azure AD JWT. Returns the claims dict."""
    from jose import jwt, JWTError

    config = get_config()
    tenant_id = config.azure_ad_tenant_id
    client_id = config.azure_ad_client_id

    jwks = _get_jwks(tenant_id)

    # Accept both v1 and v2 issuer formats
    issuers = [
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    ]
    # Accept both plain client ID and api:// prefixed audience
    audiences = [client_id, f"api://{client_id}"]

    # Log unverified claims for debugging
    try:
        unverified = jwt.get_unverified_claims(token)
        logger.info(f"Token iss={unverified.get('iss')}, aud={unverified.get('aud')}")
    except Exception:
        pass

    for issuer in issuers:
        for audience in audiences:
            try:
                payload = jwt.decode(
                    token,
                    jwks,
                    algorithms=["RS256"],
                    audience=audience,
                    issuer=issuer,
                )
                return payload
            except JWTError:
                continue

    # All combinations failed — log and raise
    logger.warning("JWT validation failed: no valid issuer/audience combination")
    raise HTTPException(401, "Invalid or expired token")


async def _upsert_user(db: AsyncSession, claims: dict) -> User:
    """Create or update a user from Azure AD token claims."""
    azure_ad_id = claims.get("oid") or claims.get("sub")
    email = claims.get("preferred_username") or claims.get("email", "")
    display_name = claims.get("name", "")

    result = await db.execute(select(User).where(User.azure_ad_id == azure_ad_id))
    user = result.scalar_one_or_none()

    if user:
        user.email = email
        user.display_name = display_name
    else:
        user = User(
            azure_ad_id=azure_ad_id,
            email=email,
            display_name=display_name,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency: extract and validate the user from the request.
    - If Azure AD is configured: validates Bearer token, upserts user.
    - If not configured: returns a dev user (for local development).
    """
    config = get_config()

    if not config.azure_ad_tenant_id:
        # Dev mode — no auth required
        result = await db.execute(select(User).where(User.email == "dev@localhost"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email="dev@localhost", display_name="Dev User")
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    # Production mode — validate Azure AD JWT
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header[7:]
    claims = _decode_token(token)
    return await _upsert_user(db, claims)
