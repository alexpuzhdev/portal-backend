"""FastAPI Depends-функции модуля auth.

Это публичный API auth-модуля для других модулей: они получают
`current_user`, `current_organization`, CSRF-проверку именно отсюда.
Никогда не читай user_id или organization_id из тела запроса — только
через эти зависимости.
"""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Path, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import Settings, get_settings
from app.modules.organizations.domain.repositories import OrganizationRepository
from app.modules.organizations.infrastructure.persistence.repositories import (
    SqlOrganizationRepository,
)
from app.shared.infrastructure.db import get_session
from app.shared.infrastructure.db.engine import get_engine

from ..application.ports import (
    Enforcer,
    PasswordHasher,
    TokenDenylist,
    TokenIssuer,
)
from ..application.use_cases.create_user import CreateUser
from ..application.use_cases.get_current_user import GetCurrentUser
from ..application.use_cases.login import Login
from ..application.use_cases.logout import Logout
from ..application.use_cases.refresh_access_token import RefreshAccessToken
from ..domain.exceptions import InactiveUser, TokenExpired, TokenInvalid
from ..domain.repositories import (
    MembershipRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from ..infrastructure.casbin.enforcer import CasbinEnforcer, build_enforcer
from ..infrastructure.persistence.repositories import (
    SqlMembershipRepository,
    SqlRefreshTokenRepository,
    SqlRoleRepository,
    SqlUserRepository,
)
from ..infrastructure.security.password_hasher import Argon2PasswordHasher
from ..infrastructure.security.token_denylist import RedisTokenDenylist
from ..infrastructure.security.token_issuer import JwtTokenIssuer

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _password_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


@lru_cache(maxsize=1)
def _redis_client(redis_url: str) -> Redis:
    client: Redis = Redis.from_url(redis_url, decode_responses=True)
    return client


_enforcer_cache: CasbinEnforcer | None = None


async def get_password_hasher() -> PasswordHasher:
    return _password_hasher()


async def get_token_issuer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenIssuer:
    return JwtTokenIssuer(settings)


async def get_token_denylist(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenDenylist:
    return RedisTokenDenylist(_redis_client(settings.redis_url))


async def get_enforcer(
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> Enforcer:
    global _enforcer_cache
    if _enforcer_cache is None:
        _enforcer_cache = await build_enforcer(engine)
    return _enforcer_cache


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRepository:
    return SqlUserRepository(session)


def get_role_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RoleRepository:
    return SqlRoleRepository(session)


def get_membership_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MembershipRepository:
    return SqlMembershipRepository(session)


def get_refresh_token_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RefreshTokenRepository:
    return SqlRefreshTokenRepository(session)


def _get_organization_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OrganizationRepository:
    return SqlOrganizationRepository(session)


# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------


def get_create_user(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
) -> CreateUser:
    return CreateUser(user_repository=user_repository, password_hasher=password_hasher)


def get_login(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_repository: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
) -> Login:
    return Login(
        user_repository=user_repository,
        refresh_token_repository=refresh_repository,
        password_hasher=password_hasher,
        token_issuer=token_issuer,
    )


def get_logout(
    refresh_repository: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
    token_issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
    denylist: Annotated[TokenDenylist, Depends(get_token_denylist)],
) -> Logout:
    return Logout(
        refresh_token_repository=refresh_repository,
        token_issuer=token_issuer,
        denylist=denylist,
    )


def get_refresh_access_token(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    refresh_repository: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)],
    token_issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
) -> RefreshAccessToken:
    return RefreshAccessToken(
        user_repository=user_repository,
        refresh_token_repository=refresh_repository,
        token_issuer=token_issuer,
    )


def get_get_current_user(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    membership_repository: Annotated[MembershipRepository, Depends(get_membership_repository)],
    role_repository: Annotated[RoleRepository, Depends(get_role_repository)],
    organization_repository: Annotated[
        OrganizationRepository, Depends(_get_organization_repository)
    ],
) -> GetCurrentUser:
    return GetCurrentUser(
        user_repository=user_repository,
        membership_repository=membership_repository,
        role_repository=role_repository,
        organization_repository=organization_repository,
    )


# ---------------------------------------------------------------------------
# Auth context (used by other modules' routes)
# ---------------------------------------------------------------------------


def _read_access_cookie(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.access_cookie_name)


async def current_user_id(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    token_issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
    denylist: Annotated[TokenDenylist, Depends(get_token_denylist)],
) -> UUID:
    access_token = _read_access_cookie(request, settings)
    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    try:
        claims = token_issuer.decode_access(access_token)
    except TokenExpired as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="access token expired") from exc
    except TokenInvalid as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid access token") from exc
    if await denylist.contains(claims.jti):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token revoked")
    return claims.user_id


async def current_user(
    user_id: Annotated[UUID, Depends(current_user_id)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UUID:
    user = await user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="user not found")
    try:
        user.assert_can_login()
    except InactiveUser as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="user is inactive") from exc
    return user.id


async def current_organization(
    org_slug: Annotated[str, Path()],
    user_id: Annotated[UUID, Depends(current_user)],
    organization_repository: Annotated[
        OrganizationRepository, Depends(_get_organization_repository)
    ],
    membership_repository: Annotated[MembershipRepository, Depends(get_membership_repository)],
) -> UUID:
    organization = await organization_repository.get_by_slug(org_slug)
    if organization is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="organization not found")
    if not organization.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="organization is disabled")
    membership = await membership_repository.get_for_user_in_organization(user_id, organization.id)
    if membership is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="no membership in this organization",
        )
    return organization.id


async def assert_csrf(
    request: Request,
    csrf_token_cookie: Annotated[str | None, Cookie(alias="portal_csrf")] = None,
    csrf_token_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if not csrf_token_cookie or not csrf_token_header:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="csrf token missing")
    if csrf_token_cookie != csrf_token_header:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="csrf token mismatch")
