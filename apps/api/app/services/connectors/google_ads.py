"""
Google Ads connector — responsive search ads via Google Ads API v17.
Credentials: { developer_token, client_id, client_secret, refresh_token, customer_id }

Phase 3 scope: create a responsive search ad in an existing ad group.
OAuth token refresh is handled inline — swap for Vault/KMS in production.
"""

from typing import Any

import httpx

from app.services.connectors.base import ConnectorAdapter, ConnectorPayload, ConnectorResult, ConnectorStatus

GOOGLE_ADS_API = "https://googleads.googleapis.com/v17"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleAdsConnector(ConnectorAdapter):
    provider = "google_ads"
    supported_channels = ["ad"]

    async def _refresh_access_token(self, credentials: dict[str, Any]) -> str | None:
        """Exchange refresh_token for a short-lived access_token."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": credentials.get("client_id", ""),
                        "client_secret": credentials.get("client_secret", ""),
                        "refresh_token": credentials.get("refresh_token", ""),
                        "grant_type": "refresh_token",
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    return resp.json().get("access_token")
        except Exception:
            pass
        return None

    async def validate(self, credentials: dict[str, Any]) -> ConnectorStatus:
        developer_token = credentials.get("developer_token", "")
        customer_id = credentials.get("customer_id", "").replace("-", "")
        if not all([developer_token, customer_id]):
            return ConnectorStatus(
                connected=False, provider=self.provider,
                error="developer_token and customer_id are required",
            )
        access_token = await self._refresh_access_token(credentials)
        if not access_token:
            return ConnectorStatus(connected=False, provider=self.provider, error="Could not refresh OAuth token")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{GOOGLE_ADS_API}/customers/{customer_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "developer-token": developer_token,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorStatus(
                        connected=True, provider=self.provider,
                        detail={
                            "customer_id": customer_id,
                            "descriptive_name": data.get("descriptiveName", ""),
                        },
                    )
                return ConnectorStatus(connected=False, provider=self.provider,
                                       error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorStatus(connected=False, provider=self.provider, error=str(e))

    async def publish(self, payload: ConnectorPayload, credentials: dict[str, Any]) -> ConnectorResult:
        """
        Creates a responsive search ad (RSA) in an existing ad group.
        Requires: developer_token, customer_id, ad_group_id (extra or credentials),
                  plus OAuth: client_id, client_secret, refresh_token
        """
        developer_token = credentials.get("developer_token", "")
        customer_id = credentials.get("customer_id", "").replace("-", "")
        ad_group_id = payload.extra.get("ad_group_id") or credentials.get("ad_group_id", "")

        if not all([developer_token, customer_id, ad_group_id]):
            return ConnectorResult(
                success=False, status="failed",
                error="developer_token, customer_id, and ad_group_id are required",
            )

        access_token = await self._refresh_access_token(credentials)
        if not access_token:
            return ConnectorResult(success=False, status="failed", error="Could not refresh OAuth token")

        # Build headlines and descriptions for RSA
        headlines = [{"text": hl} for hl in [payload.headline, payload.cta, payload.description[:30]] if hl][:15]
        descriptions = [{"text": d} for d in [payload.description, payload.text_body[:90]] if d][:4]

        if not headlines:
            return ConnectorResult(success=False, status="failed", error="No headline content available")

        mutate_body = {
            "operations": [{
                "create": {
                    "adGroup": f"customers/{customer_id}/adGroups/{ad_group_id}",
                    "status": "PAUSED",
                    "ad": {
                        "responsiveSearchAd": {
                            "headlines": headlines,
                            "descriptions": descriptions or [{"text": "Learn more today"}],
                        },
                        "finalUrls": [payload.extra.get("final_url", "https://example.com")],
                    },
                }
            }]
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GOOGLE_ADS_API}/customers/{customer_id}/adGroupAds:mutate",
                    json=mutate_body,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "developer-token": developer_token,
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    resource = result.get("results", [{}])[0].get("resourceName", "")
                    return ConnectorResult(
                        success=True,
                        provider_job_id=resource,
                        raw_response=result,
                        status="delivered",
                    )
                return ConnectorResult(
                    success=False, status="failed",
                    error=f"Google Ads {resp.status_code}: {resp.text[:300]}",
                )
        except Exception as e:
            return ConnectorResult(success=False, status="failed", error=str(e))
