import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    action: str,
    resource_type: str,
    actor_id: uuid.UUID | None = None,
    actor_email: str | None = None,
    resource_id: str | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary,
        extra=metadata or {},
    )
    db.add(entry)
    await db.flush()
    return entry
