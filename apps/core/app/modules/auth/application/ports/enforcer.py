from typing import Protocol
from uuid import UUID


class Enforcer(Protocol):
    """RBAC-enforcer: проверяет, может ли пользователь выполнить
    действие над ресурсом в контексте организации.

    Реализация — Casbin с моделью RBAC with domain (см. ADR-0010 и
    infrastructure/casbin/). Policy хранится в БД, изменяется через
    обычные SQL-операции; enforcer перечитывает её по требованию.
    """

    async def enforce(
        self, user_id: UUID, organization_id: UUID, resource: str, action: str
    ) -> bool: ...

    async def add_role_for_user_in_organization(
        self, user_id: UUID, role_name: str, organization_id: UUID
    ) -> None: ...

    async def get_roles_for_user_in_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> list[str]: ...

    async def get_permissions_for_user_in_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> list[tuple[str, str]]:
        """Список (resource, action), доступных пользователю в
        организации. Используется в /auth/me для отдачи фронту полного
        permission-set."""
        ...
