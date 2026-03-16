"""Make user_id NOT NULL on all domain tables and user_settings.

Two-phase migration step (c): after the backfill in 008b, all rows
have a valid user_id. This migration enforces the NOT NULL constraint.

Revision ID: 008c_user_id_not_null
Revises: 008b_user_id_nullable
Create Date: 2026-03-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008c_user_id_not_null"
down_revision: Union[str, None] = "008b_user_id_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tables that received user_id — domain models + user_settings
ALL_TABLES = [
    "accounts",
    "categories",
    "transactions",
    "transfers",
    "dashboards",
    "dashboard_widgets",
    "user_settings",
]


def upgrade() -> None:
    for table in ALL_TABLES:
        op.alter_column(table, "user_id", nullable=False)


def downgrade() -> None:
    for table in reversed(ALL_TABLES):
        op.alter_column(table, "user_id", nullable=True)
