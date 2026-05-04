from typing import Annotated

from fastapi import Depends

from app.modules.organizations.application.use_cases.create_root_organization import (
    CreateRootOrganization,
)
from app.modules.organizations.presentation.deps import get_create_root_organization

from ..application.setup_instance import SetupInstance


def get_setup_instance(
    create_root_organization: Annotated[
        CreateRootOrganization, Depends(get_create_root_organization)
    ],
) -> SetupInstance:
    return SetupInstance(create_root_organization=create_root_organization)
