from dataclasses import dataclass
from uuid import UUID

from app.modules.organizations.domain.repositories import OrganizationRepository

from ...domain.exceptions import UserNotFound
from ...domain.repositories import MembershipRepository, RoleRepository, UserRepository
from ..dto import CurrentUserOutput, MembershipOutput, UserOutput


@dataclass
class GetCurrentUser:
    """Возвращает профиль текущего пользователя + список memberships
    (с org slug/name и ролью). Используется фронтом сразу после login,
    чтобы построить редирект (single membership → /portal/<slug>,
    multiple → /select-org)."""

    user_repository: UserRepository
    membership_repository: MembershipRepository
    role_repository: RoleRepository
    organization_repository: OrganizationRepository

    async def execute(self, user_id: UUID) -> CurrentUserOutput:
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFound

        memberships = await self.membership_repository.list_for_user(user_id)
        outputs: list[MembershipOutput] = []
        for membership in memberships:
            organization = await self.organization_repository.get_by_id(membership.organization_id)
            role = await self.role_repository.get_by_id(membership.role_id)
            if organization is None or role is None:
                continue
            outputs.append(
                MembershipOutput(
                    id=membership.id,
                    organization_id=organization.id,
                    organization_slug=str(organization.slug),
                    organization_name=organization.name,
                    role_id=role.id,
                    role_name=role.name,
                )
            )

        return CurrentUserOutput(
            user=UserOutput.from_entity(user),
            memberships=outputs,
        )
