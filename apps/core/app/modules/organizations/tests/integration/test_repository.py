from uuid import uuid4

import pytest
from app.modules.organizations.domain.entities import Organization
from app.modules.organizations.domain.value_objects import INN, KPP, HSLColor, Slug
from app.modules.organizations.infrastructure.persistence.repositories import (
    SqlOrganizationRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_add_and_get_by_slug(db_session: AsyncSession) -> None:
    repo = SqlOrganizationRepository(db_session)
    org = Organization(
        id=uuid4(),
        slug=Slug("alpha"),
        name="Alpha",
        inn=INN("7704123456"),
        kpp=KPP("770401001"),
        primary_color_hsl=HSLColor("222 47% 11%"),
    )
    await repo.add(org)

    fetched = await repo.get_by_slug("alpha")
    assert fetched is not None
    assert fetched.id == org.id
    assert fetched.name == "Alpha"
    assert str(fetched.inn) == "7704123456"
    assert str(fetched.primary_color_hsl) == "222 47% 11%"


@pytest.mark.asyncio
async def test_get_root(db_session: AsyncSession) -> None:
    repo = SqlOrganizationRepository(db_session)
    root = Organization(id=uuid4(), slug=Slug("holding"), name="Holding")
    await repo.add(root)

    fetched_root = await repo.get_root()
    assert fetched_root is not None
    assert fetched_root.id == root.id


@pytest.mark.asyncio
async def test_update_persists_changes(db_session: AsyncSession) -> None:
    repo = SqlOrganizationRepository(db_session)
    org = Organization(id=uuid4(), slug=Slug("alpha"), name="Alpha")
    await repo.add(org)

    org.rename("Alpha Holding")
    org.enable_storefront()
    await repo.update(org)

    fetched = await repo.get_by_id(org.id)
    assert fetched is not None
    assert fetched.name == "Alpha Holding"
    assert fetched.storefront_enabled is True


@pytest.mark.asyncio
async def test_list_children(db_session: AsyncSession) -> None:
    repo = SqlOrganizationRepository(db_session)
    root = Organization(id=uuid4(), slug=Slug("holding"), name="Holding")
    await repo.add(root)
    moscow = Organization(
        id=uuid4(),
        slug=Slug("moscow"),
        name="Moscow",
        parent_organization_id=root.id,
    )
    spb = Organization(
        id=uuid4(),
        slug=Slug("spb"),
        name="Saint Petersburg",
        parent_organization_id=root.id,
    )
    await repo.add(moscow)
    await repo.add(spb)

    children = await repo.list_children(root.id)
    assert {c.slug.value for c in children} == {"moscow", "spb"}
