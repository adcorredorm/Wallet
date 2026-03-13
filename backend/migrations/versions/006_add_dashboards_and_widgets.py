"""Add dashboards and dashboard_widgets tables.

Revision ID: 006_add_dashboards_and_widgets
Revises: 005_consolidated_drop_recreate
Create Date: 2026-03-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_add_dashboards_and_widgets"
down_revision: Union[str, None] = "005_consolidated_drop_recreate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM type for widget_type
    widgettype_enum = postgresql.ENUM(
        "line", "pie", "bar", "stacked_bar", "number",
        name="widgettype",
        create_type=True,
    )
    widgettype_enum.create(op.get_bind(), checkfirst=True)

    # dashboards table
    op.create_table(
        "dashboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("display_currency", sa.String(10), nullable=False),
        sa.Column("layout_columns", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "layout_columns >= 1 AND layout_columns <= 4",
            name="ck_dashboards_layout_columns",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index("idx_dashboards_client_id", "dashboards", ["client_id"], unique=True)
    op.create_index("idx_dashboards_sort_order", "dashboards", ["sort_order"])

    # dashboard_widgets table
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(100), nullable=True),
        sa.Column(
            "dashboard_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dashboards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "widget_type",
            postgresql.ENUM(
                "line", "pie", "bar", "stacked_bar", "number",
                name="widgettype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("position_x", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_y", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("width >= 1 AND width <= 4", name="ck_widgets_width"),
        sa.CheckConstraint("height >= 1 AND height <= 3", name="ck_widgets_height"),
        sa.CheckConstraint("position_x >= 0", name="ck_widgets_position_x"),
        sa.CheckConstraint("position_y >= 0", name="ck_widgets_position_y"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index(
        "idx_dashboard_widgets_dashboard_id",
        "dashboard_widgets",
        ["dashboard_id"],
    )


def downgrade() -> None:
    op.drop_table("dashboard_widgets")
    op.drop_table("dashboards")
    op.execute("DROP TYPE IF EXISTS widgettype")
