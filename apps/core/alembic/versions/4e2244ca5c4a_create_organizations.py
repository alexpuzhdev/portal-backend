"""create organizations

Revision ID: 4e2244ca5c4a
Revises:
Create Date: 2026-04-30 14:28:09.594979

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4e2244ca5c4a"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_organization_id", sa.UUID(), nullable=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("inn", sa.String(length=12), nullable=True),
        sa.Column("kpp", sa.String(length=9), nullable=True),
        sa.Column("primary_color_hsl", sa.String(length=32), nullable=True),
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "storefront_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_organization_id"],
            ["organizations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_organizations_parent_organization_id"),
        "organizations",
        ["parent_organization_id"],
        unique=False,
    )
    # Корень холдинга — ровно один. Реализуем через partial unique index
    # по строкам с parent_organization_id IS NULL.
    op.create_index(
        "uq_organizations_single_root",
        "organizations",
        ["parent_organization_id"],
        unique=True,
        postgresql_where=sa.text("parent_organization_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_organizations_single_root", table_name="organizations")
    op.drop_index(
        op.f("ix_organizations_parent_organization_id"),
        table_name="organizations",
    )
    op.drop_table("organizations")
