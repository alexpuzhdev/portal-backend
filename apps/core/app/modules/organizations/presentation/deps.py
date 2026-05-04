from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.db import get_session

from ..application.use_cases.create_root_organization import CreateRootOrganization
from ..application.use_cases.get_organization import GetOrganizationById, GetOrganizationBySlug
from ..application.use_cases.list_organizations import ListOrganizations
from ..application.use_cases.update_organization import UpdateOrganization
from ..infrastructure.persistence.repositories import SqlOrganizationRepository


def get_organization_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SqlOrganizationRepository:
    return SqlOrganizationRepository(session)


def get_create_root_organization(
    repository: Annotated[SqlOrganizationRepository, Depends(get_organization_repository)],
) -> CreateRootOrganization:
    return CreateRootOrganization(repository=repository)


def get_get_organization_by_slug(
    repository: Annotated[SqlOrganizationRepository, Depends(get_organization_repository)],
) -> GetOrganizationBySlug:
    return GetOrganizationBySlug(repository=repository)


def get_get_organization_by_id(
    repository: Annotated[SqlOrganizationRepository, Depends(get_organization_repository)],
) -> GetOrganizationById:
    return GetOrganizationById(repository=repository)


def get_list_organizations(
    repository: Annotated[SqlOrganizationRepository, Depends(get_organization_repository)],
) -> ListOrganizations:
    return ListOrganizations(repository=repository)


def get_update_organization(
    repository: Annotated[SqlOrganizationRepository, Depends(get_organization_repository)],
) -> UpdateOrganization:
    return UpdateOrganization(repository=repository)
