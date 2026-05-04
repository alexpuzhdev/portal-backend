from ...domain.entities import Membership, RefreshToken, Role, User
from ...domain.value_objects import Email, HashedPassword
from .orm import RefreshTokenORM, RoleORM, UserOrganizationMembershipORM, UserORM


class UserMapper:
    @staticmethod
    def to_entity(orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=Email(orm.email),
            hashed_password=HashedPassword(orm.hashed_password),
            full_name=orm.full_name,
            display_name=orm.display_name,
            avatar_url=orm.avatar_url,
            phone=orm.phone,
            is_active=orm.is_active,
            email_verified_at=orm.email_verified_at,
            last_login_at=orm.last_login_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def to_orm(entity: User) -> UserORM:
        return UserORM(
            id=entity.id,
            email=str(entity.email),
            hashed_password=str(entity.hashed_password),
            full_name=entity.full_name,
            display_name=entity.display_name,
            avatar_url=entity.avatar_url,
            phone=entity.phone,
            is_active=entity.is_active,
            email_verified_at=entity.email_verified_at,
            last_login_at=entity.last_login_at,
        )


class RoleMapper:
    @staticmethod
    def to_entity(orm: RoleORM) -> Role:
        return Role(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            is_system=orm.is_system,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def to_orm(entity: Role) -> RoleORM:
        return RoleORM(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            is_system=entity.is_system,
        )


class MembershipMapper:
    @staticmethod
    def to_entity(orm: UserOrganizationMembershipORM) -> Membership:
        return Membership(
            id=orm.id,
            user_id=orm.user_id,
            organization_id=orm.organization_id,
            role_id=orm.role_id,
            created_at=orm.created_at,
        )

    @staticmethod
    def to_orm(entity: Membership) -> UserOrganizationMembershipORM:
        return UserOrganizationMembershipORM(
            id=entity.id,
            user_id=entity.user_id,
            organization_id=entity.organization_id,
            role_id=entity.role_id,
        )


class RefreshTokenMapper:
    @staticmethod
    def to_entity(orm: RefreshTokenORM) -> RefreshToken:
        return RefreshToken(
            id=orm.id,
            user_id=orm.user_id,
            token_hash=orm.token_hash,
            issued_at=orm.issued_at,
            expires_at=orm.expires_at,
            is_revoked=orm.is_revoked,
            replaced_by_id=orm.replaced_by_id,
            user_agent=orm.user_agent,
            ip_address=orm.ip_address,
        )

    @staticmethod
    def to_orm(entity: RefreshToken) -> RefreshTokenORM:
        return RefreshTokenORM(
            id=entity.id,
            user_id=entity.user_id,
            token_hash=entity.token_hash,
            issued_at=entity.issued_at,
            expires_at=entity.expires_at,
            is_revoked=entity.is_revoked,
            replaced_by_id=entity.replaced_by_id,
            user_agent=entity.user_agent,
            ip_address=entity.ip_address,
        )
