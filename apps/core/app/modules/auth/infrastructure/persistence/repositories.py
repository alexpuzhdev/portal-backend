from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities import Membership, RefreshToken, Role, User
from .mappers import MembershipMapper, RefreshTokenMapper, RoleMapper, UserMapper
from .orm import (
    RefreshTokenORM,
    RoleORM,
    UserOrganizationMembershipORM,
    UserORM,
)


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        orm = await self._session.get(UserORM, user_id)
        return UserMapper.to_entity(orm) if orm else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == email)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return UserMapper.to_entity(orm) if orm else None

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        stmt = select(UserORM).order_by(UserORM.created_at).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [UserMapper.to_entity(orm) for orm in result.scalars()]

    async def count(self) -> int:
        stmt = select(func.count()).select_from(UserORM)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def add(self, user: User) -> None:
        self._session.add(UserMapper.to_orm(user))
        await self._session.flush()

    async def update(self, user: User) -> None:
        orm = await self._session.get(UserORM, user.id)
        if orm is None:
            raise ValueError(f"user {user.id} not found")
        orm.email = str(user.email)
        orm.hashed_password = str(user.hashed_password)
        orm.full_name = user.full_name
        orm.display_name = user.display_name
        orm.avatar_url = user.avatar_url
        orm.phone = user.phone
        orm.is_active = user.is_active
        orm.email_verified_at = user.email_verified_at
        orm.last_login_at = user.last_login_at
        await self._session.flush()


class SqlRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, role_id: UUID) -> Role | None:
        orm = await self._session.get(RoleORM, role_id)
        return RoleMapper.to_entity(orm) if orm else None

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(RoleORM).where(RoleORM.name == name)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return RoleMapper.to_entity(orm) if orm else None

    async def list_all(self) -> list[Role]:
        stmt = select(RoleORM).order_by(RoleORM.name)
        result = await self._session.execute(stmt)
        return [RoleMapper.to_entity(orm) for orm in result.scalars()]

    async def add(self, role: Role) -> None:
        self._session.add(RoleMapper.to_orm(role))
        await self._session.flush()


class SqlMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, membership_id: UUID) -> Membership | None:
        orm = await self._session.get(UserOrganizationMembershipORM, membership_id)
        return MembershipMapper.to_entity(orm) if orm else None

    async def get_for_user_in_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> Membership | None:
        stmt = select(UserOrganizationMembershipORM).where(
            UserOrganizationMembershipORM.user_id == user_id,
            UserOrganizationMembershipORM.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return MembershipMapper.to_entity(orm) if orm else None

    async def list_for_user(self, user_id: UUID) -> list[Membership]:
        stmt = (
            select(UserOrganizationMembershipORM)
            .where(UserOrganizationMembershipORM.user_id == user_id)
            .order_by(UserOrganizationMembershipORM.created_at)
        )
        result = await self._session.execute(stmt)
        return [MembershipMapper.to_entity(orm) for orm in result.scalars()]

    async def list_for_organization(self, organization_id: UUID) -> list[Membership]:
        stmt = (
            select(UserOrganizationMembershipORM)
            .where(UserOrganizationMembershipORM.organization_id == organization_id)
            .order_by(UserOrganizationMembershipORM.created_at)
        )
        result = await self._session.execute(stmt)
        return [MembershipMapper.to_entity(orm) for orm in result.scalars()]

    async def add(self, membership: Membership) -> None:
        self._session.add(MembershipMapper.to_orm(membership))
        await self._session.flush()

    async def remove(self, membership_id: UUID) -> None:
        orm = await self._session.get(UserOrganizationMembershipORM, membership_id)
        if orm is None:
            return
        await self._session.delete(orm)
        await self._session.flush()


class SqlRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return RefreshTokenMapper.to_entity(orm) if orm else None

    async def add(self, token: RefreshToken) -> None:
        self._session.add(RefreshTokenMapper.to_orm(token))
        await self._session.flush()

    async def update(self, token: RefreshToken) -> None:
        orm = await self._session.get(RefreshTokenORM, token.id)
        if orm is None:
            raise ValueError(f"refresh token {token.id} not found")
        orm.is_revoked = token.is_revoked
        orm.replaced_by_id = token.replaced_by_id
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id, RefreshTokenORM.is_revoked.is_(False))
            .values(is_revoked=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()
