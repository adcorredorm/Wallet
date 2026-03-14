"""Add active column to categories table.

Revision ID: 007_add_active_to_categories
Revises: 006_add_dashboards_and_widgets
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_add_active_to_categories"
down_revision: Union[str, None] = "006_add_dashboards_and_widgets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("categories", "active")
