"""
Webflow connector — publish landing page content via Webflow CMS API v2.
Credentials: { api_key, site_id, collection_id }

Phase 3 scope: create a new CMS item (landing page) in a Webflow collection,
then publish the site to push it live.
"""

from typing import Any

import httpx

from app.services.connectors.base import ConnectorAdapter, ConnectorPayload, ConnectorResult, ConnectorStatus

WEBFLOW_API = "https://api.webflow.com/v2"


class WebflowConnector(ConnectorAdapter):
    provider = "webflow"
    supported_channels = ["landing_page"]

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "accept": "application/json",
        }

    async def validate(self, credentials: dict[str, Any]) -> ConnectorStatus:
        api_key = credentials.get("api_key", "")
        if not api_key:
            return ConnectorStatus(connected=False, provider=self.provider, error="No api_key in credentials")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{WEBFLOW_API}/token/introspect",
                    headers=self._headers(api_key),
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorStatus(
                        connected=True, provider=self.provider,
                        detail={"sites": [s.get("id") for s in data.get("sites", [])]},
                    )
                return ConnectorStatus(connected=False, provider=self.provider, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorStatus(connected=False, provider=self.provider, error=str(e))

    async def publish(self, payload: ConnectorPayload, credentials: dict[str, Any]) -> ConnectorResult:
        """
        Creates a CMS item in the specified collection and publishes the site.
        Field mapping assumes a standard landing page collection schema:
          slug, name, headline, subheadline, body, cta
        Customize collection_id and field names per your Webflow site schema.
        """
        api_key = credentials.get("api_key", "")
        site_id = payload.extra.get("site_id") or credentials.get("site_id", "")
        collection_id = payload.extra.get("collection_id") or credentials.get("collection_id", "")

        if not all([api_key, site_id, collection_id]):
            return ConnectorResult(
                success=False, status="failed",
                error="api_key, site_id, and collection_id are required",
            )

        import re
        slug = re.sub(r"[^a-z0-9-]", "-", (payload.headline or "page").lower())[:60]

        item_body: dict[str, Any] = {
            "fieldData": {
                "name": payload.headline or "New Page",
                "slug": slug,
                "headline": payload.headline,
                "body": payload.html_body or payload.text_body or payload.caption,
                "cta": payload.cta,
            },
            "isDraft": False,
            "isArchived": False,
        }

        try:
            async with httpx.AsyncClient() as client:
                # Create CMS item
                item_resp = await client.post(
                    f"{WEBFLOW_API}/collections/{collection_id}/items",
                    json=item_body,
                    headers=self._headers(api_key),
                    timeout=30,
                )
                if item_resp.status_code not in (200, 202):
                    return ConnectorResult(
                        success=False, status="failed",
                        error=f"Webflow item create failed: {item_resp.status_code} {item_resp.text[:200]}",
                    )
                item_id = item_resp.json()["id"]

                # Publish site
                pub_resp = await client.post(
                    f"{WEBFLOW_API}/sites/{site_id}/publish",
                    json={"publishToWebflowSubdomain": True},
                    headers=self._headers(api_key),
                    timeout=30,
                )

                return ConnectorResult(
                    success=True,
                    provider_job_id=item_id,
                    raw_response={
                        "item_id": item_id,
                        "publish_status": pub_resp.status_code,
                        "slug": slug,
                    },
                    status="delivered",
                )
        except Exception as e:
            return ConnectorResult(success=False, status="failed", error=str(e))
