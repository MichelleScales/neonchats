import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_slug: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    roles: list[str] = []


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str = "content_operator"


class UserRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
