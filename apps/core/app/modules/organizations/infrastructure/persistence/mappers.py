from ...domain.entities import Organization
from ...domain.value_objects import INN, KPP, HSLColor, Slug
from .orm import OrganizationORM


class OrganizationMapper:
    @staticmethod
    def to_entity(orm: OrganizationORM) -> Organization:
        return Organization(
            id=orm.id,
            slug=Slug(orm.slug),
            name=orm.name,
            parent_organization_id=orm.parent_organization_id,
            legal_name=orm.legal_name,
            inn=INN(orm.inn) if orm.inn else None,
            kpp=KPP(orm.kpp) if orm.kpp else None,
            primary_color_hsl=HSLColor(orm.primary_color_hsl) if orm.primary_color_hsl else None,
            logo_url=orm.logo_url,
            storefront_enabled=orm.storefront_enabled,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def to_orm(entity: Organization) -> OrganizationORM:
        return OrganizationORM(
            id=entity.id,
            slug=str(entity.slug),
            name=entity.name,
            parent_organization_id=entity.parent_organization_id,
            legal_name=entity.legal_name,
            inn=str(entity.inn) if entity.inn else None,
            kpp=str(entity.kpp) if entity.kpp else None,
            primary_color_hsl=str(entity.primary_color_hsl) if entity.primary_color_hsl else None,
            logo_url=entity.logo_url,
            storefront_enabled=entity.storefront_enabled,
            is_active=entity.is_active,
        )
