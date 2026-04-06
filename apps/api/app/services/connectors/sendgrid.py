"""
SendGrid connector — email delivery via v3 API.
Credentials: { api_key, from_email }
"""

from typing import Any

import httpx

from app.services.connectors.base import ConnectorAdapter, ConnectorPayload, ConnectorResult, ConnectorStatus

SENDGRID_API = "https://api.sendgrid.com/v3"


class SendGridConnector(ConnectorAdapter):
    provider = "sendgrid"
    supported_channels = ["email"]

    async def validate(self, credentials: dict[str, Any]) -> ConnectorStatus:
        api_key = credentials.get("api_key", "")
        if not api_key:
            return ConnectorStatus(connected=False, provider=self.provider, error="No api_key in credentials")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{SENDGRID_API}/user/profile",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ConnectorStatus(
                        connected=True,
                        provider=self.provider,
                        detail={"username": data.get("username"), "email": data.get("email")},
                    )
                return ConnectorStatus(connected=False, provider=self.provider, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return ConnectorStatus(connected=False, provider=self.provider, error=str(e))

    async def publish(self, payload: ConnectorPayload, credentials: dict[str, Any]) -> ConnectorResult:
        api_key = credentials.get("api_key", "")
        from_email = credentials.get("from_email", "noreply@example.com")

        if not payload.to_emails:
            return ConnectorResult(success=False, status="failed", error="No recipients")

        body = {
            "personalizations": [{"to": [{"email": e} for e in payload.to_emails]}],
            "from": {"email": from_email},
            "subject": payload.subject or "(no subject)",
            "content": [
                {"type": "text/plain", "value": payload.text_body or payload.html_body or ""},
                {"type": "text/html", "value": payload.html_body or payload.text_body or ""},
            ],
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SENDGRID_API}/mail/send",
                    json=body,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    timeout=30,
                )
                resp.raise_for_status()
                message_id = resp.headers.get("X-Message-Id")
                return ConnectorResult(
                    success=True,
                    provider_job_id=message_id,
                    raw_response={"status_code": resp.status_code, "message_id": message_id},
                    status="delivered",
                )
        except httpx.HTTPStatusError as e:
            return ConnectorResult(success=False, status="failed",
                                   error=f"SendGrid {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            return ConnectorResult(success=False, status="failed", error=str(e))
