from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models.tenant import Tenant
from app.routers.deps import DB
from app.schemas.auth import LoginRequest, Token, TokenData
from app.services.auth import authenticate_user, create_access_token, get_user_roles
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login(payload: LoginRequest, db: DB):
    # Resolve tenant
    result = await db.execute(select(Tenant).where(Tenant.slug == payload.tenant_slug, Tenant.is_active == True))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = await authenticate_user(db, tenant.id, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    roles = await get_user_roles(db, user.id)
    token = create_access_token(
        TokenData(user_id=user.id, tenant_id=tenant.id, email=user.email, roles=roles)
    )
    return Token(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
