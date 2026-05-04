from dataclasses import dataclass
from uuid import UUID

from ...domain.exceptions import OrganizationNotFound
from ...domain.repositories import OrganizationRepository
from ..dto import OrganizationOutput


@dataclass
class GetOrganizationBySlug:
    repository: OrganizationRepository

    async def execute(self, slug: str) -> OrganizationOutput:
        organization = await self.repository.get_by_slug(slug)
        if organization is None:
            raise OrganizationNotFound(slug)
        return OrganizationOutput.from_entity(organization)


@dataclass
class GetOrganizationById:
    repository: OrganizationRepository

    async def execute(self, organization_id: UUID) -> OrganizationOutput:
        organization = await self.repository.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFound(str(organization_id))
        return OrganizationOutput.from_entity(organization)
