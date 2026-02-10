"""
Microsoft Graph API email sending via client credentials flow.
Sends emails with attachments using the /users/{mailbox}/sendMail endpoint.
When GRAPH_CLIENT_SECRET is not configured, logs the payload (dry-run mode).
"""
from __future__ import annotations
import base64
import logging
import time
from typing import Optional

import httpx

from backend.config import get_config

logger = logging.getLogger(__name__)

_token_cache: dict = {}


def _get_access_token() -> str:
    """Acquire an access token using client credentials flow, with caching."""
    config = get_config()
    now = time.time()

    if _token_cache.get("token") and _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["token"]

    resp = httpx.post(
        f"https://login.microsoftonline.com/{config.graph_tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": config.graph_client_id,
            "client_secret": config.graph_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)

    return _token_cache["token"]


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_email_body(fields: dict) -> str:
    """Build a professional handoff email from extracted fields."""
    client_name = _esc(fields.get("client_name", "New Client"))
    description = _esc(fields.get("company_description", ""))
    contract_amount = _esc(fields.get("contract_amount", ""))
    service_scope = _esc(fields.get("service_scope", ""))
    go_live = _esc(fields.get("go_live_date", ""))
    users = _esc(fields.get("number_of_users", ""))
    devices = _esc(fields.get("number_of_devices", ""))
    account_team = _esc(fields.get("account_team", ""))
    pain_points = _esc(fields.get("pain_points", ""))
    primary_contact = _esc(fields.get("primary_contact", ""))

    # Build the contract details line
    contract_parts = []
    if contract_amount:
        contract_parts.append(contract_amount)
    if service_scope:
        contract_parts.append(service_scope)
    if go_live:
        contract_parts.append(f"Onboarding start: {go_live}")
    contract_line = " | ".join(contract_parts) if contract_parts else "—"

    # Build environment line
    env_parts = []
    if users:
        env_parts.append(f"{users} users")
    if devices:
        env_parts.append(f"{devices} machines")
    env_line = ", ".join(env_parts) if env_parts else "—"

    # Format pain points as bullet list
    pain_html = ""
    if pain_points:
        # Split on periods or newlines to create bullets
        points = [p.strip() for p in pain_points.replace("\n", ". ").split(". ") if p.strip()]
        if len(points) > 1:
            bullets = "".join(f"<li>{p.rstrip('.')}</li>" for p in points)
            pain_html = f'<ul style="margin:4px 0 0 0;padding-left:20px">{bullets}</ul>'
        else:
            pain_html = f"<p style='margin:4px 0 0 0'>{pain_points.replace(chr(10), '<br>')}</p>"

    s = "font-family:Arial,sans-serif;color:#1f2937;line-height:1.6"
    h = "color:#1E4488;font-size:14px;font-weight:700;margin:20px 0 6px 0"

    return f"""\
<html>
<body style="{s}">
<p>Team,</p>
<p>We've signed a new client &mdash; here's what you need to know:</p>

<p>{description or client_name}</p>

<p style="{h}">Primary Contact</p>
<p style="margin:0">{primary_contact or '—'}</p>

<p style="{h}">Contract</p>
<p style="margin:0"><strong>{contract_line}</strong></p>

<p style="{h}">Environment</p>
<p style="margin:0">{env_line}</p>

<p style="{h}">Account Team</p>
<p style="margin:0">{account_team or '—'}</p>

<p style="{h}">Why They're Switching</p>
{pain_html or '<p style="margin:0">—</p>'}

<p style="margin-top:24px">The full onboarding workbook is attached, along with the signed SOW and MSA.</p>

<p style="color:#9ca3af;font-size:12px;margin-top:32px">
Sent by the Onboarding Form Filler system.
</p>
</body>
</html>"""


def send_email(
    to_emails: list[str],
    subject: str,
    html_body: str,
    attachments: Optional[list[dict]] = None,
) -> dict:
    """
    Send an email via Graph API from the configured mailbox.

    attachments: list of {filename: str, content_bytes: bytes, content_type: str}

    Returns {"status": "sent"} on success or {"status": "dry_run", ...} in dev mode.
    """
    config = get_config()
    attachments = attachments or []

    if not config.graph_client_secret:
        logger.info(
            "DRY RUN — email not sent (no GRAPH_CLIENT_SECRET)\n"
            "  To: %s\n  Subject: %s\n  Attachments: %s",
            to_emails,
            subject,
            [a["filename"] for a in attachments],
        )
        return {
            "status": "dry_run",
            "to": to_emails,
            "subject": subject,
            "attachment_count": len(attachments),
        }

    token = _get_access_token()

    graph_attachments = [
        {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": a["filename"],
            "contentType": a["content_type"],
            "contentBytes": base64.b64encode(a["content_bytes"]).decode(),
        }
        for a in attachments
    ]

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [
                {"emailAddress": {"address": e}} for e in to_emails
            ],
            "attachments": graph_attachments,
        }
    }

    resp = httpx.post(
        f"https://graph.microsoft.com/v1.0/users/{config.graph_send_from_email}/sendMail",
        json=message,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()

    logger.info("Email sent to %s — subject: %s", to_emails, subject)
    return {"status": "sent"}
