from pydantic import BaseModel

from app.modules.organizations.presentation.schemas import (
    CreateRootOrganizationRequest,
    OrganizationResponse,
)


class SetupRequest(BaseModel):
    """Запрос на инициализацию инстанса.

    В Блоке 2 эта схема расширится owner-полями (email, full_name,
    password). Сейчас содержит только данные корневой организации,
    чтобы каркас инициализации был отдельно проверяемым.
    """

    organization: CreateRootOrganizationRequest


class SetupResponse(BaseModel):
    organization: OrganizationResponse
