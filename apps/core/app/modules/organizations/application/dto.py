from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..domain.entities import Organization


@dataclass(frozen=True)
class CreateRootOrganizationInput:
    slug: str
    name: str
    legal_name: str | None = None
    inn: str | None = None
    kpp: str | None = None
    primary_color_hsl: str | None = None


@dataclass(frozen=True)
class UpdateOrganizationInput:
    organization_id: UUID
    name: str | None = None
    legal_name: str | None = None
    inn: str | None = None
    kpp: str | None = None
    primary_color_hsl: str | None = None
    logo_url: str | None = None
    storefront_enabled: bool | None = None


@dataclass(frozen=True)
class OrganizationOutput:
    id: UUID
    slug: str
    name: str
    parent_organization_id: UUID | None
    legal_name: str | None
    inn: str | None
    kpp: str | None
    primary_color_hsl: str | None
    logo_url: str | None
    storefront_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, org: Organization) -> "OrganizationOutput":
        return cls(
            id=org.id,
            slug=str(org.slug),
            name=org.name,
            parent_organization_id=org.parent_organization_id,
            legal_name=org.legal_name,
            inn=str(org.inn) if org.inn else None,
            kpp=str(org.kpp) if org.kpp else None,
            primary_color_hsl=str(org.primary_color_hsl) if org.primary_color_hsl else None,
            logo_url=org.logo_url,
            storefront_enabled=org.storefront_enabled,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )
