"""
Meta Ads connector — Facebook/Instagram ad creative via Marketing API v19.
Credentials: { access_token, ad_account_id, page_id?, pixel_id? }

Phase 3 scope: create ad creative + ad, publish to an existing ad set.
Full campaign creation (objective, targeting, budget) deferred to Phase 4.
"""

from typing import Any

import httpx

from app.services.connectors.base import ConnectorAdapter, ConnectorPayload, ConnectorResult, ConnectorStatus

META_API = "https://graph.facebook.com/v19.0"


class MetaAdsConnector(ConnectorAdapter):
    provider = "meta_ads"
    supported_channels = ["social", "ad"]

    async def validate(self, credentials: dict[str, Any]) -> ConnectorStatus:
        token = credentials.get("access_token", "")
        if not token:
            return ConnectorStatus(connected=False, provider=self.provider, error="No access_token in credentials")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{META_API}/me",
                    params={"access_token": token, "fields": "id,name,email"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorStatus(
                        connected=True, provider=self.provider,
                        detail={"id": data.get("id"), "name": data.get("name")},
                    )
                return ConnectorStatus(connected=False, provider=self.provider, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorStatus(connected=False, provider=self.provider, error=str(e))

    async def publish(self, payload: ConnectorPayload, credentials: dict[str, Any]) -> ConnectorResult:
        """
        Creates an ad creative and ad in an existing ad set.
        Requires: access_token, ad_account_id, ad_set_id (in extra or credentials).
        """
        token = credentials.get("access_token", "")
        ad_account_id = credentials.get("ad_account_id", "")
        ad_set_id = payload.extra.get("ad_set_id") or credentials.get("ad_set_id", "")
        page_id = payload.extra.get("page_id") or credentials.get("page_id", "")

        if not all([token, ad_account_id, ad_set_id]):
            return ConnectorResult(
                success=False, status="failed",
                error="access_token, ad_account_id, and ad_set_id are required",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Create ad creative
                creative_data: dict[str, Any] = {
                    "name": f"EMP Creative {payload.asset_id[:8]}",
                    "object_story_spec": {
                        "page_id": page_id,
                        "link_data": {
                            "message": payload.caption or payload.description,
                            "name": payload.headline,
                            "description": payload.description,
                            "call_to_action": {"type": "LEARN_MORE"},
                        },
                    },
                }
                if payload.image_url:
                    creative_data["object_story_spec"]["link_data"]["picture"] = payload.image_url

                creative_resp = await client.post(
                    f"{META_API}/act_{ad_account_id}/adcreatives",
                    params={"access_token": token},
                    json=creative_data,
                    timeout=30,
                )
                if creative_resp.status_code != 200:
                    return ConnectorResult(
                        success=False, status="failed",
                        error=f"Meta creative failed: {creative_resp.status_code} {creative_resp.text[:200]}",
                    )
                creative_id = creative_resp.json()["id"]

                # Step 2: Create ad in the ad set
                ad_resp = await client.post(
                    f"{META_API}/act_{ad_account_id}/ads",
                    params={"access_token": token},
                    json={
                        "name": f"EMP Ad {payload.asset_id[:8]}",
                        "adset_id": ad_set_id,
                        "creative": {"creative_id": creative_id},
                        "status": "PAUSED",  # Start paused — requires manual activation
                    },
                    timeout=30,
                )
                if ad_resp.status_code != 200:
                    return ConnectorResult(
                        success=False, status="failed",
                        error=f"Meta ad creation failed: {ad_resp.status_code} {ad_resp.text[:200]}",
                    )
                ad_id = ad_resp.json()["id"]

                return ConnectorResult(
                    success=True,
                    provider_job_id=ad_id,
                    raw_response={"creative_id": creative_id, "ad_id": ad_id, "status": "PAUSED"},
                    status="delivered",
                )
        except Exception as e:
            return ConnectorResult(success=False, status="failed", error=str(e))
