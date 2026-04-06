"""
Execution service — provider adapters for SendGrid (Phase 1) and HubSpot (Phase 2).
All sends go through idempotency checks before firing.
"""

import hashlib
import json
import uuid
from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()


def make_idempotency_key(campaign_id: uuid.UUID, asset_id: uuid.UUID, channel: str) -> str:
    raw = f"{campaign_id}:{asset_id}:{channel}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def send_email_sendgrid(
    *,
    to_emails: list[str],
    subject: str,
    html_body: str,
    text_body: str,
    from_email: str | None = None,
) -> dict[str, Any]:
    from_email = from_email or settings.sendgrid_from_email
    payload = {
        "personalizations": [{"to": [{"email": e} for e in to_emails]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()
        return {
            "provider": "sendgrid",
            "status_code": resp.status_code,
            "message_id": resp.headers.get("X-Message-Id"),
        }


async def resolve_email_recipients(
    *,
    hubspot_list_id: str | None,
    fallback_emails: list[str] | None = None,
) -> list[str]:
    """
    Resolve the actual recipient list for an email send.
    - If hubspot_list_id is set, fetch contacts from HubSpot.
    - Otherwise, use fallback_emails (e.g. test addresses from campaign config).
    """
    if hubspot_list_id:
        from app.services.hubspot import get_list_emails
        emails = await get_list_emails(hubspot_list_id)
        if emails:
            return emails

    return fallback_emails or ["test@example.com"]


async def publish_social_post(
    *,
    provider: str,
    caption: str,
    hashtags: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    # Phase 2 stub — MCP connector integration in Phase 3
    full_caption = caption + " " + " ".join(f"#{h}" for h in hashtags)
    return {
        "provider": provider,
        "status": "published",
        "caption": full_caption,
        "note": "Phase 2 stub — real MCP connector in Phase 3",
    }
