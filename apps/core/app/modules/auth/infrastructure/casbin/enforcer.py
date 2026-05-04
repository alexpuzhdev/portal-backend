from pathlib import Path
from uuid import UUID

import casbin
from casbin_async_sqlalchemy_adapter import Adapter
from sqlalchemy.ext.asyncio import AsyncEngine

_MODEL_PATH = Path(__file__).parent / "model.conf"


class CasbinEnforcer:
    """Casbin AsyncEnforcer обёрнут в наш Enforcer port. Адаптер
    хранит policy в той же Postgres-БД (см. ADR-0010, развилка A1).

    Создаётся через фабрику `build_enforcer` — async-контекст для
    инициализации adapter.
    """

    def __init__(self, enforcer: casbin.AsyncEnforcer) -> None:
        self._enforcer = enforcer

    async def enforce(
        self, user_id: UUID, organization_id: UUID, resource: str, action: str
    ) -> bool:
        return bool(
            await self._enforcer.enforce(str(user_id), str(organization_id), resource, action)
        )

    async def add_role_for_user_in_organization(
        self, user_id: UUID, role_name: str, organization_id: UUID
    ) -> None:
        await self._enforcer.add_grouping_policy(str(user_id), role_name, str(organization_id))

    async def get_roles_for_user_in_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> list[str]:
        return list(await self._enforcer.get_roles_for_user(str(user_id), str(organization_id)))

    async def get_permissions_for_user_in_organization(
        self, user_id: UUID, organization_id: UUID
    ) -> list[tuple[str, str]]:
        roles = await self._enforcer.get_roles_for_user(str(user_id), str(organization_id))
        permissions: set[tuple[str, str]] = set()
        for role in roles:
            for policy in await self._enforcer.get_filtered_policy(0, role):
                # policy = [sub, dom, obj, act]
                if len(policy) < 4:
                    continue
                dom = policy[1]
                if dom not in ("*", str(organization_id)):
                    continue
                permissions.add((policy[2], policy[3]))
        return sorted(permissions)


async def build_enforcer(engine: AsyncEngine) -> CasbinEnforcer:
    adapter = Adapter(engine)
    await adapter.create_table()
    enforcer = casbin.AsyncEnforcer(str(_MODEL_PATH), adapter)
    await enforcer.load_policy()
    return CasbinEnforcer(enforcer)
