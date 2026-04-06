"""
Klaviyo connector — email and SMS via Klaviyo API v2024-02-15.
Credentials: { api_key, list_id? }

Supports:
  - email: send campaign to a Klaviyo list
  - sms: send SMS campaign to a Klaviyo list
"""

from typing import Any

import httpx

from app.services.connectors.base import ConnectorAdapter, ConnectorPayload, ConnectorResult, ConnectorStatus

KLAVIYO_API = "https://a.klaviyo.com/api"


class KlaviyoConnector(ConnectorAdapter):
    provider = "klaviyo"
    supported_channels = ["email", "sms"]

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Klaviyo-API-Key {api_key}",
            "revision": "2024-02-15",
            "Content-Type": "application/json",
        }

    async def validate(self, credentials: dict[str, Any]) -> ConnectorStatus:
        api_key = credentials.get("api_key", "")
        if not api_key:
            return ConnectorStatus(connected=False, provider=self.provider, error="No api_key in credentials")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{KLAVIYO_API}/accounts",
                    headers=self._headers(api_key),
                    timeout=10,
                )
                if resp.status_code == 200:
                    accounts = resp.json().get("data", [])
                    detail = accounts[0].get("attributes", {}) if accounts else {}
                    return ConnectorStatus(connected=True, provider=self.provider, detail=detail)
                return ConnectorStatus(connected=False, provider=self.provider, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorStatus(connected=False, provider=self.provider, error=str(e))

    async def publish(self, payload: ConnectorPayload, credentials: dict[str, Any]) -> ConnectorResult:
        """
        Creates a one-time Klaviyo campaign send using the Campaigns API.
        Requires list_id in credentials or payload.extra.
        """
        api_key = credentials.get("api_key", "")
        list_id = payload.extra.get("klaviyo_list_id") or credentials.get("list_id", "")

        if not list_id:
            return ConnectorResult(success=False, status="failed",
                                   error="klaviyo_list_id required in credentials or payload.extra")

        channel_type = "EMAIL" if payload.channel == "email" else "SMS"

        # Step 1: Create campaign
        campaign_body = {
            "data": {
                "type": "campaign",
                "attributes": {
                    "name": f"EMP-{payload.campaign_id[:8]}",
                    "channel": channel_type,
                    "audiences": {"included": [list_id]},
                    "send_options": {"use_smart_sending": True},
                    "campaign-messages": {
                        "data": [{
                            "type": "campaign-message",
                            "attributes": {
                                "label": payload.subject or "Campaign message",
                                "content": {
                                    "subject": payload.subject,
                                    "preview_text": "",
                                    "from_email": credentials.get("from_email", ""),
                                    "from_label": credentials.get("from_label", ""),
                                    "body": payload.html_body or payload.text_body or payload.caption,
                                },
                            },
                        }]
                    },
                },
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                # Create campaign
                resp = await client.post(
                    f"{KLAVIYO_API}/campaigns",
                    json=campaign_body,
                    headers=self._headers(api_key),
                    timeout=30,
                )
                if resp.status_code not in (200, 201):
                    return ConnectorResult(
                        success=False, status="failed",
                        error=f"Klaviyo create campaign failed: {resp.status_code} {resp.text[:200]}"
                    )
                campaign_id = resp.json()["data"]["id"]

                # Step 2: Schedule as immediate send
                send_resp = await client.post(
                    f"{KLAVIYO_API}/campaign-send-jobs",
                    json={"data": {"type": "campaign-send-job", "attributes": {"campaign_id": campaign_id}}},
                    headers=self._headers(api_key),
                    timeout=30,
                )
                send_resp.raise_for_status()
                job_id = send_resp.json()["data"]["id"]

                return ConnectorResult(
                    success=True,
                    provider_job_id=job_id,
                    raw_response={"campaign_id": campaign_id, "send_job_id": job_id},
                    status="dispatched",
                )
        except httpx.HTTPStatusError as e:
            return ConnectorResult(success=False, status="failed",
                                   error=f"Klaviyo {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            return ConnectorResult(success=False, status="failed", error=str(e))

    async def get_job_status(self, provider_job_id: str, credentials: dict[str, Any]) -> str:
        api_key = credentials.get("api_key", "")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{KLAVIYO_API}/campaign-send-jobs/{provider_job_id}",
                    headers=self._headers(api_key),
                    timeout=10,
                )
                if resp.status_code == 200:
                    status = resp.json()["data"]["attributes"].get("status", "")
                    return {
                        "queued": "queued",
                        "processing": "dispatched",
                        "cancelled": "failed",
                        "complete": "delivered",
                    }.get(status, "dispatched")
        except Exception:
            pass
        return "dispatched"
