from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.application.ports import Enforcer
from app.modules.auth.application.use_cases.create_user import CreateUser
from app.modules.auth.domain.repositories import MembershipRepository, RoleRepository
from app.modules.auth.infrastructure.casbin.enforcer import CasbinEnforcer
from app.modules.auth.presentation.deps import (
    get_create_user,
    get_enforcer,
    get_membership_repository,
    get_role_repository,
)
from app.modules.organizations.application.use_cases.create_root_organization import (
    CreateRootOrganization,
)
from app.modules.organizations.presentation.deps import get_create_root_organization
from app.shared.infrastructure.db import get_session

from ..application.setup_instance import SetupInstance


def get_setup_instance(
    create_root_organization: Annotated[
        CreateRootOrganization, Depends(get_create_root_organization)
    ],
    create_user: Annotated[CreateUser, Depends(get_create_user)],
    role_repository: Annotated[RoleRepository, Depends(get_role_repository)],
    membership_repository: Annotated[MembershipRepository, Depends(get_membership_repository)],
    enforcer: Annotated[Enforcer, Depends(get_enforcer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SetupInstance:
    # SetupInstance ожидает CasbinEnforcer для доступа к raw policy
    # (см. setup_instance.py); cast здесь безопасен, т.к. в проде
    # реализация всегда CasbinEnforcer (см. presentation/deps.py).
    assert isinstance(enforcer, CasbinEnforcer)
    return SetupInstance(
        create_root_organization=create_root_organization,
        create_user=create_user,
        role_repository=role_repository,
        membership_repository=membership_repository,
        enforcer=enforcer,
        session=session,
    )
