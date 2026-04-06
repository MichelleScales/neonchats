"""
Integrations router — connection status checks and list fetching for HubSpot.
"""

from fastapi import APIRouter, HTTPException
from typing import Any

from app.routers.deps import DB, CurrentUser
from app.services.hubspot import get_lists, verify_connection
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status")
async def integration_status(user: CurrentUser) -> dict[str, Any]:
    """Return connection status for all configured integrations."""
    hubspot = await verify_connection()
    return {
        "sendgrid": {
            "connected": bool(settings.sendgrid_api_key),
            "from_email": settings.sendgrid_from_email if settings.sendgrid_api_key else None,
        },
        "hubspot": hubspot,
        "google_ads": {"connected": False},
        "meta_ads": {"connected": False},
        "klaviyo": {"connected": False},
        "webflow": {"connected": False},
    }


@router.get("/hubspot/lists")
async def hubspot_lists(user: CurrentUser) -> list[dict[str, Any]]:
    """Fetch available HubSpot contact lists for audience targeting."""
    if not settings.hubspot_access_token:
        raise HTTPException(status_code=400, detail="HubSpot not configured. Add HUBSPOT_ACCESS_TOKEN to .env")
    try:
        return await get_lists()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"HubSpot error: {str(e)}")
