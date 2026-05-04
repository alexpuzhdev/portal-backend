from dataclasses import dataclass

from app.modules.organizations.application.dto import (
    CreateRootOrganizationInput,
    OrganizationOutput,
)
from app.modules.organizations.application.use_cases.create_root_organization import (
    CreateRootOrganization,
)


@dataclass
class SetupInstance:
    """Инициализирует инстанс Portal: создаёт корневую организацию
    холдинга. В Блоке 2 этап расширится — здесь же будет создан первый
    owner и его membership.

    Сейчас защита one-time-only обеспечивается через RootOrganizationAlreadyExists
    в нижележащем UseCase: повторный вызов после первого успешного будет
    отклонён.
    """

    create_root_organization: CreateRootOrganization

    async def execute(self, organization: CreateRootOrganizationInput) -> OrganizationOutput:
        return await self.create_root_organization.execute(organization)
