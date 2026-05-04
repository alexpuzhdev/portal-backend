from uuid import uuid4

import pytest
from app.modules.organizations.application.dto import (
    CreateRootOrganizationInput,
    UpdateOrganizationInput,
)
from app.modules.organizations.application.use_cases.create_root_organization import (
    CreateRootOrganization,
)
from app.modules.organizations.application.use_cases.get_organization import (
    GetOrganizationById,
    GetOrganizationBySlug,
)
from app.modules.organizations.application.use_cases.list_organizations import ListOrganizations
from app.modules.organizations.application.use_cases.update_organization import UpdateOrganization
from app.modules.organizations.domain.exceptions import OrganizationNotFound

from .fake_repository import FakeOrganizationRepository


async def test_get_by_slug_found() -> None:
    repo = FakeOrganizationRepository()
    create = CreateRootOrganization(repository=repo)
    created = await create.execute(CreateRootOrganizationInput(slug="alpha", name="Alpha"))

    output = await GetOrganizationBySlug(repository=repo).execute("alpha")
    assert output.id == created.id


async def test_get_by_slug_not_found() -> None:
    repo = FakeOrganizationRepository()
    with pytest.raises(OrganizationNotFound):
        await GetOrganizationBySlug(repository=repo).execute("missing")


async def test_get_by_id_not_found() -> None:
    repo = FakeOrganizationRepository()
    with pytest.raises(OrganizationNotFound):
        await GetOrganizationById(repository=repo).execute(uuid4())


async def test_list_returns_all() -> None:
    repo = FakeOrganizationRepository()
    create = CreateRootOrganization(repository=repo)
    await create.execute(CreateRootOrganizationInput(slug="alpha", name="Alpha"))

    listing = await ListOrganizations(repository=repo).execute()
    assert len(listing) == 1
    assert listing[0].slug == "alpha"


async def test_update_changes_fields() -> None:
    repo = FakeOrganizationRepository()
    create = CreateRootOrganization(repository=repo)
    created = await create.execute(CreateRootOrganizationInput(slug="alpha", name="Alpha"))

    updated = await UpdateOrganization(repository=repo).execute(
        UpdateOrganizationInput(
            organization_id=created.id,
            name="Alpha Holding",
            primary_color_hsl="222 47% 11%",
            storefront_enabled=True,
        )
    )

    assert updated.name == "Alpha Holding"
    assert updated.primary_color_hsl == "222 47% 11%"
    assert updated.storefront_enabled is True


async def test_update_clears_optional_field_with_empty_string() -> None:
    repo = FakeOrganizationRepository()
    create = CreateRootOrganization(repository=repo)
    created = await create.execute(
        CreateRootOrganizationInput(slug="alpha", name="Alpha", legal_name="ООО Альфа")
    )

    updated = await UpdateOrganization(repository=repo).execute(
        UpdateOrganizationInput(organization_id=created.id, legal_name="")
    )

    assert updated.legal_name is None
