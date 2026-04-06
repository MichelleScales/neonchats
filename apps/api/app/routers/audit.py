from fastapi import APIRouter, Query
from sqlalchemy import select

from app.models.audit import AuditLog
from app.routers.deps import DB, CurrentUser
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    db: DB,
    user: CurrentUser,
    action: str | None = None,
    resource_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    if "workspace_admin" not in user.roles and "analyst" not in user.roles:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    q = (
        select(AuditLog)
        .where(AuditLog.tenant_id == user.tenant_id)
        .order_by(AuditLog.occurred_at.desc())
    )
    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return result.scalars().all()
