"""
HubSpot integration service.
Handles contact list fetching and email address resolution for campaign sends.
Uses the HubSpot API v3 with a private app access token (simplest auth for Phase 2).

Setup:
  1. In HubSpot: Settings → Integrations → Private Apps → Create
  2. Scopes needed: crm.lists.read, crm.objects.contacts.read
  3. Copy the access token to .env: HUBSPOT_ACCESS_TOKEN=pat-...
"""

from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()

HUBSPOT_BASE = "https://api.hubapi.com"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.hubspot_access_token}",
        "Content-Type": "application/json",
    }


async def get_lists() -> list[dict[str, Any]]:
    """Fetch all static/active contact lists from HubSpot."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{HUBSPOT_BASE}/contacts/v1/lists",
            headers=_headers(),
            params={"count": 250},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": str(lst["listId"]),
                "name": lst["name"],
                "size": lst.get("metaData", {}).get("size", 0),
                "list_type": lst.get("listType", "STATIC"),
            }
            for lst in data.get("lists", [])
        ]


async def get_list_emails(list_id: str, max_contacts: int = 500) -> list[str]:
    """
    Fetch email addresses for all contacts in a HubSpot list.
    Returns up to max_contacts emails (Phase 2 limit).
    """
    emails: list[str] = []
    vid_offset = 0

    async with httpx.AsyncClient() as client:
        while len(emails) < max_contacts:
            resp = await client.get(
                f"{HUBSPOT_BASE}/contacts/v1/lists/{list_id}/contacts/all",
                headers=_headers(),
                params={
                    "count": 100,
                    "vidOffset": vid_offset,
                    "property": "email",
                },
                timeout=15,
            )
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()

            for contact in data.get("contacts", []):
                for prop in contact.get("identity-profiles", []):
                    for identity in prop.get("identities", []):
                        if identity.get("type") == "EMAIL":
                            emails.append(identity["value"])

            if not data.get("has-more"):
                break
            vid_offset = data.get("vid-offset", 0)

    return list(set(emails))[:max_contacts]


async def get_contact_by_email(email: str) -> dict[str, Any] | None:
    """Look up a single HubSpot contact by email."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{HUBSPOT_BASE}/contacts/v1/contact/email/{email}/profile",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        props = data.get("properties", {})
        return {
            "vid": data.get("vid"),
            "email": email,
            "first_name": props.get("firstname", {}).get("value", ""),
            "last_name": props.get("lastname", {}).get("value", ""),
            "company": props.get("company", {}).get("value", ""),
        }


async def verify_connection() -> dict[str, Any]:
    """Test the HubSpot connection and return account info."""
    if not settings.hubspot_access_token:
        return {"connected": False, "error": "No access token configured"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{HUBSPOT_BASE}/integrations/v1/me",
                headers=_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"connected": True, "portal_id": data.get("portalId"), "hub_domain": data.get("hubDomain")}
            return {"connected": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"connected": False, "error": str(e)}
