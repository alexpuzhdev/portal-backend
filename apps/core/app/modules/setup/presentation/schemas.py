from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.presentation.schemas import UserResponse
from app.modules.organizations.presentation.schemas import (
    CreateRootOrganizationRequest,
    OrganizationResponse,
)


class SetupOwnerRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=512)
    full_name: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)


class SetupRequest(BaseModel):
    organization: CreateRootOrganizationRequest
    owner: SetupOwnerRequest


class SetupResponse(BaseModel):
    organization: OrganizationResponse
    owner: UserResponse
