from dataclasses import dataclass

from ...domain.exceptions import OrganizationNotFound
from ...domain.repositories import OrganizationRepository
from ...domain.value_objects import INN, KPP, HSLColor
from ..dto import OrganizationOutput, UpdateOrganizationInput


@dataclass
class UpdateOrganization:
    repository: OrganizationRepository

    async def execute(self, input_dto: UpdateOrganizationInput) -> OrganizationOutput:
        organization = await self.repository.get_by_id(input_dto.organization_id)
        if organization is None:
            raise OrganizationNotFound(str(input_dto.organization_id))

        if input_dto.name is not None:
            organization.rename(input_dto.name)
        if input_dto.legal_name is not None:
            organization.legal_name = input_dto.legal_name.strip() or None
        if input_dto.inn is not None:
            organization.inn = INN(input_dto.inn) if input_dto.inn else None
        if input_dto.kpp is not None:
            organization.kpp = KPP(input_dto.kpp) if input_dto.kpp else None
        if input_dto.primary_color_hsl is not None:
            organization.primary_color_hsl = (
                HSLColor(input_dto.primary_color_hsl) if input_dto.primary_color_hsl else None
            )
        if input_dto.logo_url is not None:
            organization.logo_url = input_dto.logo_url or None
        if input_dto.storefront_enabled is not None:
            if input_dto.storefront_enabled:
                organization.enable_storefront()
            else:
                organization.disable_storefront()

        await self.repository.update(organization)
        return OrganizationOutput.from_entity(organization)
