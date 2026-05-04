import pytest
from app.modules.organizations.application.dto import CreateRootOrganizationInput
from app.modules.organizations.application.use_cases.create_root_organization import (
    CreateRootOrganization,
)
from app.modules.organizations.domain.exceptions import (
    OrganizationAlreadyExists,
    RootOrganizationAlreadyExists,
)
from app.modules.organizations.domain.value_objects import InvalidINN

from .fake_repository import FakeOrganizationRepository


async def test_creates_root_with_minimal_fields() -> None:
    repo = FakeOrganizationRepository()
    use_case = CreateRootOrganization(repository=repo)

    output = await use_case.execute(CreateRootOrganizationInput(slug="alpha", name="Alpha Holding"))

    assert output.slug == "alpha"
    assert output.name == "Alpha Holding"
    assert output.parent_organization_id is None
    assert output.is_active is True
    assert output.storefront_enabled is False
    root = await repo.get_root()
    assert root is not None
    assert root.id == output.id


async def test_creates_root_with_full_fields() -> None:
    repo = FakeOrganizationRepository()
    use_case = CreateRootOrganization(repository=repo)

    output = await use_case.execute(
        CreateRootOrganizationInput(
            slug="alpha",
            name="Alpha Holding",
            legal_name="ООО Альфа",
            inn="7704123456",
            kpp="770401001",
            primary_color_hsl="222 47% 11%",
        )
    )

    assert output.legal_name == "ООО Альфа"
    assert output.inn == "7704123456"
    assert output.kpp == "770401001"
    assert output.primary_color_hsl == "222 47% 11%"


async def test_rejects_second_root() -> None:
    repo = FakeOrganizationRepository()
    use_case = CreateRootOrganization(repository=repo)

    await use_case.execute(CreateRootOrganizationInput(slug="alpha", name="Alpha"))

    with pytest.raises(RootOrganizationAlreadyExists):
        await use_case.execute(CreateRootOrganizationInput(slug="beta", name="Beta"))


async def test_rejects_duplicate_slug_when_no_root_yet() -> None:
    """Логически невозможно при чистой репе, но проверяем contract: если
    каким-то образом slug уже занят — отказ."""
    repo = FakeOrganizationRepository()
    # Имитируем заранее посаженную не-корневую запись с тем же slug
    from uuid import uuid4

    from app.modules.organizations.domain.entities import Organization
    from app.modules.organizations.domain.value_objects import Slug

    await repo.add(
        Organization(
            id=uuid4(),
            slug=Slug("alpha"),
            name="Pre-existing",
            parent_organization_id=uuid4(),
        )
    )
    use_case = CreateRootOrganization(repository=repo)

    with pytest.raises(OrganizationAlreadyExists):
        await use_case.execute(CreateRootOrganizationInput(slug="alpha", name="Alpha"))


async def test_propagates_invalid_inn() -> None:
    repo = FakeOrganizationRepository()
    use_case = CreateRootOrganization(repository=repo)

    with pytest.raises(InvalidINN):
        await use_case.execute(
            CreateRootOrganizationInput(slug="alpha", name="A", inn="not-a-number")
        )
