from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ..application.use_cases.get_organization import GetOrganizationBySlug
from ..application.use_cases.list_organizations import ListOrganizations
from ..domain.exceptions import OrganizationNotFound
from .deps import get_get_organization_by_slug, get_list_organizations
from .schemas import OrganizationResponse

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    use_case: Annotated[ListOrganizations, Depends(get_list_organizations)],
) -> list[OrganizationResponse]:
    organizations = await use_case.execute()
    return [OrganizationResponse.model_validate(org, from_attributes=True) for org in organizations]


@router.get("/{slug}", response_model=OrganizationResponse)
async def get_organization(
    slug: str,
    use_case: Annotated[GetOrganizationBySlug, Depends(get_get_organization_by_slug)],
) -> OrganizationResponse:
    try:
        organization = await use_case.execute(slug)
    except OrganizationNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="organization not found") from exc
    return OrganizationResponse.model_validate(organization, from_attributes=True)
