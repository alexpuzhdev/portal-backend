from dataclasses import dataclass
from uuid import uuid4

from ...domain.entities import Organization
from ...domain.exceptions import OrganizationAlreadyExists, RootOrganizationAlreadyExists
from ...domain.repositories import OrganizationRepository
from ...domain.value_objects import INN, KPP, HSLColor, Slug
from ..dto import CreateRootOrganizationInput, OrganizationOutput


@dataclass
class CreateRootOrganization:
    """Создаёт корневую организацию холдинга. Допускается ровно один раз
    на инстанс — повторный вызов поднимает RootOrganizationAlreadyExists.
    """

    repository: OrganizationRepository

    async def execute(self, input_dto: CreateRootOrganizationInput) -> OrganizationOutput:
        existing_root = await self.repository.get_root()
        if existing_root is not None:
            raise RootOrganizationAlreadyExists

        if await self.repository.get_by_slug(input_dto.slug) is not None:
            raise OrganizationAlreadyExists(input_dto.slug)

        organization = Organization(
            id=uuid4(),
            slug=Slug(input_dto.slug),
            name=input_dto.name.strip(),
            parent_organization_id=None,
            legal_name=input_dto.legal_name.strip() if input_dto.legal_name else None,
            inn=INN(input_dto.inn) if input_dto.inn else None,
            kpp=KPP(input_dto.kpp) if input_dto.kpp else None,
            primary_color_hsl=(
                HSLColor(input_dto.primary_color_hsl) if input_dto.primary_color_hsl else None
            ),
        )
        await self.repository.add(organization)
        return OrganizationOutput.from_entity(organization)
