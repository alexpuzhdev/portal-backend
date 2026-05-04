from uuid import UUID, uuid4

import pytest
from app.modules.organizations.domain.entities import Organization
from app.modules.organizations.domain.exceptions import CannotDeactivateRoot
from app.modules.organizations.domain.value_objects import Slug


def make_org(*, parent_id: UUID | None = None) -> Organization:
    return Organization(
        id=uuid4(),
        slug=Slug("alpha"),
        name="Alpha",
        parent_organization_id=parent_id,
    )


class TestOrganization:
    def test_root_property(self) -> None:
        assert make_org().is_root is True
        assert make_org(parent_id=uuid4()).is_root is False

    def test_storefront_toggle(self) -> None:
        org = make_org()
        assert org.storefront_enabled is False
        org.enable_storefront()
        assert org.storefront_enabled is True
        org.disable_storefront()
        assert org.storefront_enabled is False

    def test_deactivate_non_root(self) -> None:
        org = make_org(parent_id=uuid4())
        org.deactivate()
        assert org.is_active is False

    def test_cannot_deactivate_root(self) -> None:
        with pytest.raises(CannotDeactivateRoot):
            make_org().deactivate()

    def test_rename_strips_and_updates(self) -> None:
        org = make_org()
        org.rename("  New Name  ")
        assert org.name == "New Name"

    def test_rename_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            make_org().rename("   ")
