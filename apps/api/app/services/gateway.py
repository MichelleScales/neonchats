"""
MCP Gateway — unified connector dispatch layer.

Responsibilities:
  1. Resolve which connector to use (provider + channel)
  2. Load tenant credentials from the DB
  3. Build a normalised ConnectorPayload from variant body + campaign context
  4. Dispatch through the connector
  5. Record a ConnectorJob row and update ExecutionRun
  6. Return the ConnectorResult to the caller

Every execution goes through gateway.dispatch() — no provider logic in routers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector import ConnectorCredential, ConnectorJob
from app.services.connectors.base import ConnectorAdapter, ConnectorPayload, ConnectorResult
from app.services.connectors.sendgrid import SendGridConnector
from app.services.connectors.klaviyo import KlaviyoConnector
from app.services.connectors.meta import MetaAdsConnector
from app.services.connectors.google_ads import GoogleAdsConnector
from app.services.connectors.webflow import WebflowConnector

# ── Registry ──────────────────────────────────────────────────────────────────
# Maps provider slug → connector instance.
# Add new connectors here — no other file needs changing.

_REGISTRY: dict[str, ConnectorAdapter] = {
    "sendgrid":   SendGridConnector(),
    "klaviyo":    KlaviyoConnector(),
    "meta_ads":   MetaAdsConnector(),
    "google_ads": GoogleAdsConnector(),
    "webflow":    WebflowConnector(),
}

# Static fallback credentials from settings (for backward compat with Phase 1/2)
def _settings_credentials(provider: str) -> dict[str, Any]:
    from app.config import get_settings
    s = get_settings()
    return {
        "sendgrid": {"api_key": s.sendgrid_api_key, "from_email": s.sendgrid_from_email},
        "hubspot":  {"access_token": s.hubspot_access_token},
    }.get(provider, {})


def get_connector(provider: str) -> ConnectorAdapter | None:
    return _REGISTRY.get(provider)


def list_providers() -> list[str]:
    return list(_REGISTRY.keys())


# ── Credential resolution ─────────────────────────────────────────────────────

async def resolve_credentials(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    provider: str,
) -> dict[str, Any]:
    """
    Load credentials from connector_credentials table.
    Falls back to settings-level env vars for Phase 1/2 providers.
    """
    result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.tenant_id == tenant_id,
            ConnectorCredential.provider == provider,
            ConnectorCredential.is_active == True,
        ).order_by(ConnectorCredential.created_at.desc()).limit(1)
    )
    cred = result.scalar_one_or_none()
    if cred:
        return dict(cred.credentials)
    # Fallback to env-level settings
    return _settings_credentials(provider)


# ── Payload builder ───────────────────────────────────────────────────────────

def build_payload(
    *,
    provider: str,
    channel: str,
    campaign_id: uuid.UUID,
    asset_id: uuid.UUID,
    execution_run_id: uuid.UUID,
    variant_body: dict[str, Any],
    to_emails: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> ConnectorPayload:
    """Convert a ContentVariant.body JSONB blob into a normalised ConnectorPayload."""
    return ConnectorPayload(
        provider=provider,
        channel=channel,
        campaign_id=str(campaign_id),
        asset_id=str(asset_id),
        execution_run_id=str(execution_run_id),
        # Email fields
        subject=variant_body.get("subject", ""),
        html_body=variant_body.get("html_body", ""),
        text_body=variant_body.get("text_body", ""),
        # Social / ad fields
        caption=variant_body.get("caption", ""),
        hashtags=variant_body.get("hashtags", []),
        headline=variant_body.get("headline", ""),
        description=variant_body.get("description", ""),
        cta=variant_body.get("cta", ""),
        image_url=variant_body.get("image_url", ""),
        # Email recipients
        to_emails=to_emails or [],
        extra=extra or {},
    )


# ── Main dispatch ─────────────────────────────────────────────────────────────

async def dispatch(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    provider: str,
    channel: str,
    campaign_id: uuid.UUID,
    asset_id: uuid.UUID,
    execution_run_id: uuid.UUID,
    variant_body: dict[str, Any],
    to_emails: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> ConnectorResult:
    """
    Main entry point for the MCP Gateway.
    Resolves connector → credentials → payload → dispatch → records job.
    Returns ConnectorResult for the caller to set run.status.
    """
    connector = get_connector(provider)
    if not connector:
        # Unknown provider — return a failed result, caller sets run.status="failed"
        return ConnectorResult(
            success=False,
            status="failed",
            error=f"Unknown provider '{provider}'. Available: {', '.join(list_providers())}",
        )

    credentials = await resolve_credentials(db, tenant_id=tenant_id, provider=provider)

    payload = build_payload(
        provider=provider,
        channel=channel,
        campaign_id=campaign_id,
        asset_id=asset_id,
        execution_run_id=execution_run_id,
        variant_body=variant_body,
        to_emails=to_emails,
        extra=extra,
    )

    # Create connector job record (queued)
    job = ConnectorJob(
        tenant_id=tenant_id,
        execution_run_id=execution_run_id,
        campaign_id=campaign_id,
        asset_id=asset_id,
        provider=provider,
        channel=channel,
        status="queued",
    )
    db.add(job)
    await db.flush()

    # Dispatch
    job.status = "dispatched"
    job.dispatched_at = datetime.now(timezone.utc)

    try:
        result = await connector.publish(payload, credentials)
    except Exception as exc:
        result = ConnectorResult(success=False, status="failed", error=str(exc))

    # Update job record
    job.status = result.status
    job.provider_job_id = result.provider_job_id
    job.provider_response = result.raw_response
    job.error_message = result.error
    if result.success:
        job.delivered_at = datetime.now(timezone.utc)

    return result


# ── Validation (used by integrations router) ──────────────────────────────────

async def validate_all(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Run validate() on every registered connector and return a status dict.
    Used by GET /api/integrations/status.
    """
    statuses: dict[str, Any] = {}
    for provider, connector in _REGISTRY.items():
        credentials = await resolve_credentials(db, tenant_id=tenant_id, provider=provider)
        if not credentials:
            statuses[provider] = {"connected": False, "error": "No credentials configured"}
            continue
        try:
            status = await connector.validate(credentials)
            statuses[provider] = {
                "connected": status.connected,
                "detail": status.detail,
                **({"error": status.error} if status.error else {}),
            }
        except Exception as e:
            statuses[provider] = {"connected": False, "error": str(e)}
    return statuses
