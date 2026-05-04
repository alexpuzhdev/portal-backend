from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from .exceptions import InactiveUser
from .value_objects import Email, HashedPassword


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class User:
    id: UUID
    email: Email
    hashed_password: HashedPassword
    full_name: str
    display_name: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    is_active: bool = True
    email_verified_at: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def assert_can_login(self) -> None:
        if not self.is_active:
            raise InactiveUser

    def mark_logged_in(self, at: datetime) -> None:
        self.last_login_at = at
        self.updated_at = at

    def change_password(self, new_hash: HashedPassword) -> None:
        self.hashed_password = new_hash
        self.updated_at = _utcnow()

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _utcnow()

    def reactivate(self) -> None:
        self.is_active = True
        self.updated_at = _utcnow()


@dataclass
class Role:
    """Роль с настраиваемыми permissions. Bootstrap создаёт три роли
    (`owner`, `admin`, `member`) — но они не «зашиты» в коде, их можно
    переопределять (см. project memory про Frappe-style RBAC).

    `is_system` помечает роли, защищённые от удаления через UI.
    """

    id: UUID
    name: str
    description: str | None = None
    is_system: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


@dataclass
class Membership:
    """Связь пользователя с организацией холдинга (N:M через
    membership), с одной ролью на membership."""

    id: UUID
    user_id: UUID
    organization_id: UUID
    role_id: UUID
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class RefreshToken:
    """Серверная запись refresh-токена. Сам токен не хранится — только
    его hash. При rotation один токен инвалидируется и выпускается
    новый. is_revoked == True означает logout либо использование
    уже-проrotated токена (фрод-сигнал)."""

    id: UUID
    user_id: UUID
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    is_revoked: bool = False
    replaced_by_id: UUID | None = None
    user_agent: str | None = None
    ip_address: str | None = None

    def revoke(self, replaced_by_id: UUID | None = None) -> None:
        self.is_revoked = True
        if replaced_by_id is not None:
            self.replaced_by_id = replaced_by_id
