from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.organizations.application.dto import CreateRootOrganizationInput
from app.modules.organizations.domain.exceptions import (
    OrganizationAlreadyExists,
    RootOrganizationAlreadyExists,
)
from app.modules.organizations.domain.value_objects import (
    InvalidHSLColor,
    InvalidINN,
    InvalidKPP,
    InvalidSlug,
)
from app.modules.organizations.presentation.schemas import OrganizationResponse

from ..application.setup_instance import SetupInstance
from .deps import get_setup_instance
from .schemas import SetupRequest, SetupResponse

router = APIRouter(tags=["setup"])


@router.post(
    "/setup",
    response_model=SetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize the Portal instance",
    description=(
        "One-time endpoint to bootstrap a freshly deployed Portal instance: "
        "creates the root organization of the holding. In Stage 1 Block 2 "
        "this endpoint will additionally create the first owner user. "
        "Subsequent calls return 409 Conflict."
    ),
)
async def setup_instance(
    request: SetupRequest,
    use_case: Annotated[SetupInstance, Depends(get_setup_instance)],
) -> SetupResponse:
    try:
        organization = await use_case.execute(
            CreateRootOrganizationInput(
                slug=request.organization.slug,
                name=request.organization.name,
                legal_name=request.organization.legal_name,
                inn=request.organization.inn,
                kpp=request.organization.kpp,
                primary_color_hsl=request.organization.primary_color_hsl,
            )
        )
    except RootOrganizationAlreadyExists as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="instance is already initialised",
        ) from exc
    except OrganizationAlreadyExists as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"organization with slug '{exc}' already exists",
        ) from exc
    except (InvalidSlug, InvalidINN, InvalidKPP, InvalidHSLColor) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return SetupResponse(
        organization=OrganizationResponse.model_validate(organization, from_attributes=True),
    )
