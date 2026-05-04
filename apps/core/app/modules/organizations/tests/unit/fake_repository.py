from uuid import UUID

from app.modules.organizations.domain.entities import Organization


class FakeOrganizationRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, Organization] = {}

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self._storage.get(organization_id)

    async def get_by_slug(self, slug: str) -> Organization | None:
        for org in self._storage.values():
            if str(org.slug) == slug:
                return org
        return None

    async def get_root(self) -> Organization | None:
        for org in self._storage.values():
            if org.is_root:
                return org
        return None

    async def list_all(self) -> list[Organization]:
        return list(self._storage.values())

    async def list_children(self, parent_id: UUID) -> list[Organization]:
        return [org for org in self._storage.values() if org.parent_organization_id == parent_id]

    async def add(self, organization: Organization) -> None:
        self._storage[organization.id] = organization

    async def update(self, organization: Organization) -> None:
        self._storage[organization.id] = organization
