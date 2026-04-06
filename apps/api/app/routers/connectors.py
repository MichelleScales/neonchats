"""
Connectors router — credential management and job status for the MCP Gateway.

POST   /api/connectors/credentials          — store/update credentials for a provider
GET    /api/connectors/credentials          — list configured providers (keys redacted)
DELETE /api/connectors/credentials/{id}    — deactivate credentials
POST   /api/connectors/credentials/{id}/verify — run validate() against live API
GET    /api/connectors/jobs                 — list recent connector jobs
GET    /api/connectors/jobs/{job_id}        — single job detail
GET    /api/connectors/status               — live health check on all configured connectors
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models.connector import ConnectorCredential, ConnectorJob
from app.routers.deps import DB, CurrentUser
from app.schemas.connector import ConnectorJobRead, CredentialRead, CredentialUpsert, GatewayStatusItem
from app.services import gateway
from app.services.audit import log_action

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


# ── Credentials ───────────────────────────────────────────────────────────────

@router.post("/credentials", response_model=CredentialRead, status_code=status.HTTP_201_CREATED)
async def upsert_credentials(payload: CredentialUpsert, db: DB, user: CurrentUser):
    """Store or replace credentials for a provider. Existing active creds are deactivated."""
    if "workspace_admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Only workspace_admin can manage credentials")

    # Deactivate existing credentials for this provider
    existing_result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.tenant_id == user.tenant_id,
            ConnectorCredential.provider == payload.provider,
            ConnectorCredential.is_active == True,
        )
    )
    for cred in existing_result.scalars().all():
        cred.is_active = False

    cred = ConnectorCredential(
        tenant_id=user.tenant_id,
        provider=payload.provider,
        label=payload.label,
        credentials=payload.credentials,
        is_active=True,
    )
    db.add(cred)
    await db.flush()

    await log_action(
        db, tenant_id=user.tenant_id, actor_id=user.user_id, actor_email=user.email,
        action="connector.credentials_updated", resource_type="connector_credential",
        resource_id=str(cred.id),
        summary=f"Credentials updated for {payload.provider}",
    )

    return _redact(cred)


@router.get("/credentials", response_model=list[CredentialRead])
async def list_credentials(db: DB, user: CurrentUser):
    result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.tenant_id == user.tenant_id,
            ConnectorCredential.is_active == True,
        ).order_by(ConnectorCredential.provider)
    )
    return [_redact(c) for c in result.scalars().all()]


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credentials(credential_id: uuid.UUID, db: DB, user: CurrentUser):
    if "workspace_admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Only workspace_admin can manage credentials")
    result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.id == credential_id,
            ConnectorCredential.tenant_id == user.tenant_id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    cred.is_active = False
    await log_action(
        db, tenant_id=user.tenant_id, actor_id=user.user_id, actor_email=user.email,
        action="connector.credentials_removed", resource_type="connector_credential",
        resource_id=str(credential_id), summary=f"Credentials removed for {cred.provider}",
    )


@router.post("/credentials/{credential_id}/verify", response_model=GatewayStatusItem)
async def verify_credentials(credential_id: uuid.UUID, db: DB, user: CurrentUser):
    """Run live validate() against the provider API and update last_verified_at."""
    result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.id == credential_id,
            ConnectorCredential.tenant_id == user.tenant_id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    connector = gateway.get_connector(cred.provider)
    if not connector:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {cred.provider}")

    status_result = await connector.validate(dict(cred.credentials))

    if status_result.connected:
        from datetime import datetime, timezone
        cred.last_verified_at = datetime.now(timezone.utc)

    return GatewayStatusItem(
        provider=cred.provider,
        connected=status_result.connected,
        detail=status_result.detail,
        error=status_result.error,
        has_credentials=True,
    )


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs", response_model=list[ConnectorJobRead])
async def list_jobs(
    db: DB,
    user: CurrentUser,
    campaign_id: uuid.UUID | None = None,
    provider: str | None = None,
    limit: int = 50,
):
    q = select(ConnectorJob).where(ConnectorJob.tenant_id == user.tenant_id)
    if campaign_id:
        q = q.where(ConnectorJob.campaign_id == campaign_id)
    if provider:
        q = q.where(ConnectorJob.provider == provider)
    q = q.order_by(ConnectorJob.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/jobs/{job_id}", response_model=ConnectorJobRead)
async def get_job(job_id: uuid.UUID, db: DB, user: CurrentUser):
    result = await db.execute(
        select(ConnectorJob).where(
            ConnectorJob.id == job_id,
            ConnectorJob.tenant_id == user.tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Gateway status ────────────────────────────────────────────────────────────

@router.get("/status", response_model=list[GatewayStatusItem])
async def gateway_status(db: DB, user: CurrentUser):
    """
    Live health check on every registered connector using stored credentials.
    Does NOT hit provider APIs for unconfigured connectors — just marks them as not connected.
    """
    # Load all active credentials for this tenant
    creds_result = await db.execute(
        select(ConnectorCredential).where(
            ConnectorCredential.tenant_id == user.tenant_id,
            ConnectorCredential.is_active == True,
        )
    )
    creds_by_provider = {c.provider: c for c in creds_result.scalars().all()}

    items: list[GatewayStatusItem] = []
    for provider_name in gateway.list_providers():
        cred = creds_by_provider.get(provider_name)
        if not cred:
            # Check env-level fallback (sendgrid, hubspot)
            fallback = gateway._settings_credentials(provider_name)
            has_cred = bool(fallback.get("api_key") or fallback.get("access_token"))
            items.append(GatewayStatusItem(
                provider=provider_name, connected=False,
                error="No credentials configured" if not has_cred else None,
                has_credentials=has_cred,
            ))
            continue

        connector = gateway.get_connector(provider_name)
        if not connector:
            items.append(GatewayStatusItem(provider=provider_name, connected=False, has_credentials=True))
            continue

        try:
            s = await connector.validate(dict(cred.credentials))
            items.append(GatewayStatusItem(
                provider=provider_name,
                connected=s.connected,
                detail=s.detail,
                error=s.error,
                has_credentials=True,
            ))
        except Exception as e:
            items.append(GatewayStatusItem(
                provider=provider_name, connected=False, error=str(e), has_credentials=True,
            ))

    return items


# ── Helpers ───────────────────────────────────────────────────────────────────

def _redact(cred: ConnectorCredential) -> CredentialRead:
    """Return a CredentialRead with credential keys listed but values hidden."""
    return CredentialRead(
        id=cred.id,
        tenant_id=cred.tenant_id,
        provider=cred.provider,
        label=cred.label,
        is_active=cred.is_active,
        last_verified_at=cred.last_verified_at,
        created_at=cred.created_at,
        credential_keys=list(cred.credentials.keys()),
    )
