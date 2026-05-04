from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Pydantic-валидаторы для slug/INN/KPP/HSL зеркалят domain value objects.
# Здесь они определены как обычные строки с regex — реальная проверка
# поднимается из value-objects при выполнении UseCase.

SlugStr = str
INNStr = str
KPPStr = str
HSLStr = str


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: SlugStr
    name: str
    parent_organization_id: UUID | None
    legal_name: str | None
    inn: INNStr | None
    kpp: KPPStr | None
    primary_color_hsl: HSLStr | None
    logo_url: str | None
    storefront_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreateRootOrganizationRequest(BaseModel):
    slug: SlugStr = Field(..., min_length=1, max_length=63)
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    inn: INNStr | None = Field(default=None, min_length=10, max_length=12)
    kpp: KPPStr | None = Field(default=None, min_length=9, max_length=9)
    primary_color_hsl: HSLStr | None = Field(default=None, max_length=32)


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    inn: INNStr | None = Field(default=None, min_length=10, max_length=12)
    kpp: KPPStr | None = Field(default=None, min_length=9, max_length=9)
    primary_color_hsl: HSLStr | None = Field(default=None, max_length=32)
    logo_url: str | None = Field(default=None, max_length=2048)
    storefront_enabled: bool | None = None
