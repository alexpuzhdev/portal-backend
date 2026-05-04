from dataclasses import dataclass

from ...domain.repositories import OrganizationRepository
from ..dto import OrganizationOutput


@dataclass
class ListOrganizations:
    repository: OrganizationRepository

    async def execute(self) -> list[OrganizationOutput]:
        organizations = await self.repository.list_all()
        return [OrganizationOutput.from_entity(org) for org in organizations]
