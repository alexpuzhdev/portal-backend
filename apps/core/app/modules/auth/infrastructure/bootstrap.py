"""Bootstrap auth-данных: системные роли и базовые permissions.

Запускается из миграции (data migration рядом со схемой) или вручную
через CLI/setup endpoint. Идемпотентный: повторный вызов не дублирует
записи.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .persistence.orm import PermissionORM, RoleORM, RolePermissionORM


@dataclass(frozen=True)
class _RoleSpec:
    name: str
    description: str
    permissions: tuple[tuple[str, str], ...]


# Минимальный permission-набор для Этапа 1. Расширяется по мере
# появления модулей (catalog, requests, ...). Каждое новое разрешение
# регистрируется в этой структуре + добавляется data-migration.
SYSTEM_ROLES: tuple[_RoleSpec, ...] = (
    _RoleSpec(
        name="owner",
        description="Полный контроль над инстансом и всеми организациями холдинга",
        permissions=(
            ("organizations", "read"),
            ("organizations", "update"),
            ("invitations", "create"),
            ("invitations", "list"),
            ("invitations", "revoke"),
            ("users", "list"),
            ("users", "reset_password"),
            ("memberships", "create"),
            ("memberships", "remove"),
        ),
    ),
    _RoleSpec(
        name="admin",
        description="Управление пользователями и приглашениями организации",
        permissions=(
            ("organizations", "read"),
            ("invitations", "create"),
            ("invitations", "list"),
            ("invitations", "revoke"),
            ("users", "list"),
            ("users", "reset_password"),
            ("memberships", "create"),
            ("memberships", "remove"),
        ),
    ),
    _RoleSpec(
        name="member",
        description="Обычный сотрудник организации",
        permissions=(("organizations", "read"),),
    ),
)


async def ensure_system_roles_and_permissions(
    session: AsyncSession,
) -> dict[str, UUID]:
    """Создаёт три системные роли и связанные permission-записи, если
    их ещё нет. Возвращает dict {role_name: role_id}, который нужен
    для последующего создания casbin policy.
    """
    now = datetime.now(UTC)

    # Permissions
    permission_ids: dict[tuple[str, str], UUID] = {}
    for role in SYSTEM_ROLES:
        for resource, action in role.permissions:
            key = (resource, action)
            if key in permission_ids:
                continue
            stmt = select(PermissionORM).where(
                PermissionORM.resource == resource,
                PermissionORM.action == action,
                PermissionORM.level == 0,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                permission_ids[key] = existing.id
                continue
            new_id = uuid4()
            session.add(
                PermissionORM(
                    id=new_id,
                    resource=resource,
                    action=action,
                    level=0,
                    created_at=now,
                )
            )
            permission_ids[key] = new_id

    # Roles + role_permissions
    role_ids: dict[str, UUID] = {}
    for role in SYSTEM_ROLES:
        role_stmt = select(RoleORM).where(RoleORM.name == role.name)
        existing_role = (await session.execute(role_stmt)).scalar_one_or_none()
        if existing_role is None:
            role_id = uuid4()
            session.add(
                RoleORM(
                    id=role_id,
                    name=role.name,
                    description=role.description,
                    is_system=True,
                )
            )
            role_ids[role.name] = role_id
        else:
            role_ids[role.name] = existing_role.id

        await session.flush()

        for resource, action in role.permissions:
            permission_id = permission_ids[(resource, action)]
            link_stmt = select(RolePermissionORM).where(
                RolePermissionORM.role_id == role_ids[role.name],
                RolePermissionORM.permission_id == permission_id,
            )
            link = (await session.execute(link_stmt)).scalar_one_or_none()
            if link is not None:
                continue
            session.add(
                RolePermissionORM(
                    role_id=role_ids[role.name],
                    permission_id=permission_id,
                )
            )

    await session.flush()
    return role_ids


def system_role_permissions(role_name: str) -> tuple[tuple[str, str], ...]:
    """Возвращает permissions, прописанные в SYSTEM_ROLES для данной
    роли. Используется при создании Casbin policy."""
    for role in SYSTEM_ROLES:
        if role.name == role_name:
            return role.permissions
    return ()
