from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from .exceptions import CannotDeactivateRoot
from .value_objects import INN, KPP, HSLColor, Slug


@dataclass
class Organization:
    """Структурная единица холдинга — корневой холдинг или его узел
    (юрлицо, филиал, бренд)."""

    id: UUID
    slug: Slug
    name: str
    parent_organization_id: UUID | None = None
    legal_name: str | None = None
    inn: INN | None = None
    kpp: KPP | None = None
    primary_color_hsl: HSLColor | None = None
    logo_url: str | None = None
    storefront_enabled: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime = field(default_factory=lambda: datetime.now())

    @property
    def is_root(self) -> bool:
        return self.parent_organization_id is None

    def enable_storefront(self) -> None:
        self.storefront_enabled = True
        self.updated_at = datetime.now()

    def disable_storefront(self) -> None:
        self.storefront_enabled = False
        self.updated_at = datetime.now()

    def deactivate(self) -> None:
        if self.is_root:
            raise CannotDeactivateRoot
        self.is_active = False
        self.updated_at = datetime.now()

    def reactivate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.now()

    def rename(self, new_name: str) -> None:
        if not new_name.strip():
            raise ValueError("organization name cannot be empty")
        self.name = new_name.strip()
        self.updated_at = datetime.now()
