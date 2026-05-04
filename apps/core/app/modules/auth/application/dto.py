from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..domain.entities import User


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str
    user_agent: str | None = None
    ip_address: str | None = None


@dataclass(frozen=True)
class TokensOutput:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    user_id: UUID


@dataclass(frozen=True)
class UserOutput:
    id: UUID
    email: str
    full_name: str
    display_name: str | None
    avatar_url: str | None
    phone: str | None
    is_active: bool
    email_verified_at: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserOutput":
        return cls(
            id=user.id,
            email=str(user.email),
            full_name=user.full_name,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            is_active=user.is_active,
            email_verified_at=user.email_verified_at,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


@dataclass(frozen=True)
class MembershipOutput:
    id: UUID
    organization_id: UUID
    organization_slug: str
    organization_name: str
    role_id: UUID
    role_name: str


@dataclass(frozen=True)
class CurrentUserOutput:
    user: UserOutput
    memberships: list[MembershipOutput]


@dataclass(frozen=True)
class CreateUserInput:
    email: str
    password: str
    full_name: str
    display_name: str | None = None
    phone: str | None = None
