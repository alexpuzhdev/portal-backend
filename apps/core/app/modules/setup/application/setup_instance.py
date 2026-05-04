from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import casbin
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.dto import CreateUserInput, UserOutput
from app.modules.auth.application.use_cases.create_user import CreateUser
from app.modules.auth.domain.entities import Membership
from app.modules.auth.domain.repositories import MembershipRepository, RoleRepository
from app.modules.auth.infrastructure.bootstrap import (
    ensure_system_roles_and_permissions,
    system_role_permissions,
)
from app.modules.auth.infrastructure.casbin.enforcer import CasbinEnforcer
from app.modules.organizations.application.dto import (
    CreateRootOrganizationInput,
    OrganizationOutput,
)
from app.modules.organizations.application.use_cases.create_root_organization import (
    CreateRootOrganization,
)


@dataclass
class SetupInstance:
    """Инициализирует инстанс Portal: создаёт корневую организацию,
    bootstrap'ит системные роли и permissions, создаёт первого
    пользователя-owner, прописывает membership и Casbin policy.

    Защита one-time-only обеспечивается через
    RootOrganizationAlreadyExists в нижележащем UseCase: повторный
    вызов после первого успешного будет отклонён.
    """

    create_root_organization: CreateRootOrganization
    create_user: CreateUser
    role_repository: RoleRepository
    membership_repository: MembershipRepository
    enforcer: CasbinEnforcer
    session: AsyncSession

    async def execute(
        self,
        organization: CreateRootOrganizationInput,
        owner: CreateUserInput,
    ) -> tuple[OrganizationOutput, UserOutput]:
        # 1. Bootstrap ролей и permissions. Идемпотентный — на повторе
        # ничего не дублирует. Делаем до создания организации, чтобы
        # потом сразу повесить membership с ролью owner.
        await ensure_system_roles_and_permissions(self.session)

        # 2. Корневая организация. RootOrganizationAlreadyExists →
        # подняться выше как защита от повторного setup.
        organization_output = await self.create_root_organization.execute(organization)

        # 3. Первый owner.
        user_output = await self.create_user.execute(owner)

        # 4. Membership owner-а на корневой организации.
        owner_role = await self.role_repository.get_by_name("owner")
        if owner_role is None:
            raise RuntimeError("system role 'owner' is missing after bootstrap")
        await self.membership_repository.add(
            Membership(
                id=uuid4(),
                user_id=user_output.id,
                organization_id=organization_output.id,
                role_id=owner_role.id,
                created_at=datetime.now(UTC),
            )
        )

        # 5. Casbin policy для всех системных ролей. Permissions
        # привязаны к "*" (любая организация холдинга) — какая
        # конкретно организация контролируется через grouping (g3).
        raw_enforcer = self._raw_enforcer()
        for role_name in ("owner", "admin", "member"):
            for resource, action in system_role_permissions(role_name):
                await raw_enforcer.add_policy(role_name, "*", resource, action)

        # 6. Привязываем owner к роли owner в этой организации.
        await self.enforcer.add_role_for_user_in_organization(
            user_output.id, "owner", organization_output.id
        )

        return organization_output, user_output

    def _raw_enforcer(self) -> casbin.AsyncEnforcer:
        # Доступ к внутреннему Casbin enforcer для batch-вставки
        # policy. Внешний интерфейс CasbinEnforcer этого не требует
        # каждый день — это редкая bootstrap-операция.
        return self.enforcer._enforcer
