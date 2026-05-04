from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=512)


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    display_name: str | None
    avatar_url: str | None
    phone: str | None
    is_active: bool
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MembershipResponse(BaseModel):
    id: UUID
    organization_id: UUID
    organization_slug: str
    organization_name: str
    role_id: UUID
    role_name: str


class CurrentUserResponse(BaseModel):
    user: UserResponse
    memberships: list[MembershipResponse]


class LoginResponse(BaseModel):
    """Возвращается после успешного login. Тело содержит user-профиль
    и memberships, чтобы фронт сразу мог решить, куда редиректить
    (single membership → /portal/<slug>, multiple → /select-org)."""

    user: UserResponse
    memberships: list[MembershipResponse]
