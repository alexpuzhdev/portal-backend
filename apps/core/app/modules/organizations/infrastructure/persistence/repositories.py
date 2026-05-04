from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import Organization
from .mappers import OrganizationMapper
from .orm import OrganizationORM


class SqlOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        stmt = select(OrganizationORM).where(OrganizationORM.id == organization_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return OrganizationMapper.to_entity(orm) if orm else None

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(OrganizationORM).where(OrganizationORM.slug == slug)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return OrganizationMapper.to_entity(orm) if orm else None

    async def get_root(self) -> Organization | None:
        stmt = select(OrganizationORM).where(OrganizationORM.parent_organization_id.is_(None))
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return OrganizationMapper.to_entity(orm) if orm else None

    async def list_all(self) -> list[Organization]:
        stmt = select(OrganizationORM).order_by(OrganizationORM.created_at)
        result = await self._session.execute(stmt)
        return [OrganizationMapper.to_entity(orm) for orm in result.scalars()]

    async def list_children(self, parent_id: UUID) -> list[Organization]:
        stmt = (
            select(OrganizationORM)
            .where(OrganizationORM.parent_organization_id == parent_id)
            .order_by(OrganizationORM.name)
        )
        result = await self._session.execute(stmt)
        return [OrganizationMapper.to_entity(orm) for orm in result.scalars()]

    async def add(self, organization: Organization) -> None:
        orm = OrganizationMapper.to_orm(organization)
        self._session.add(orm)
        await self._session.flush()

    async def update(self, organization: Organization) -> None:
        orm = await self._session.get(OrganizationORM, organization.id)
        if orm is None:
            raise ValueError(f"organization {organization.id} not found")
        orm.slug = str(organization.slug)
        orm.name = organization.name
        orm.parent_organization_id = organization.parent_organization_id
        orm.legal_name = organization.legal_name
        orm.inn = str(organization.inn) if organization.inn else None
        orm.kpp = str(organization.kpp) if organization.kpp else None
        orm.primary_color_hsl = (
            str(organization.primary_color_hsl) if organization.primary_color_hsl else None
        )
        orm.logo_url = organization.logo_url
        orm.storefront_enabled = organization.storefront_enabled
        orm.is_active = organization.is_active
        await self._session.flush()
