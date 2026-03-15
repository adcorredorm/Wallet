"""
DashboardWidget model for individual widgets inside a Dashboard.
"""

import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    CheckConstraint,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref

from app.models.base import BaseModel


class WidgetType(str, enum.Enum):
    """Supported chart / display types for a widget.

    Inheriting from str ensures SQLAlchemy uses the enum VALUE (lowercase)
    when persisting to PostgreSQL, not the enum NAME (uppercase). This matches
    the PostgreSQL enum type created by migration 006 which uses lowercase values.
    """

    LINE = "line"
    PIE = "pie"
    BAR = "bar"
    STACKED_BAR = "stacked_bar"
    NUMBER = "number"


class DashboardWidget(BaseModel):
    """
    A single widget inside a Dashboard.

    Each widget stores its own display configuration (time range, filters,
    granularity, grouping) in the config JSONB column.
    display_currency is inherited from the parent Dashboard — NOT stored here.
    The frontend reads that config and queries IndexedDB to produce the
    actual chart data — the backend never touches analytics.

    Attributes:
        dashboard_id: FK to the owning Dashboard (CASCADE delete).
        widget_type: Chart / display type from WidgetType enum.
        title: Widget heading (max 100 characters).
        position_x: Horizontal grid position (>= 0).
        position_y: Vertical grid position (>= 0).
        width: Grid columns occupied (1–4).
        height: Grid rows occupied (1–3).
        config: JSONB blob with frontend rendering config.
    """

    __tablename__ = "dashboard_widgets"

    dashboard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    widget_type = Column(
        # values_callable tells SQLAlchemy to use the enum VALUES (lowercase: 'bar')
        # rather than the enum NAMES (uppercase: 'BAR') when persisting to PostgreSQL.
        # This matches the PostgreSQL enum type created in migration 006 which uses
        # lowercase values ('line', 'bar', 'pie', 'stacked_bar', 'number').
        Enum(WidgetType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    title = Column(String(100), nullable=False)
    position_x = Column(Integer, nullable=False, default=0)
    position_y = Column(Integer, nullable=False, default=0)
    width = Column(Integer, nullable=False, default=1)
    height = Column(Integer, nullable=False, default=1)
    config = Column(JSONB, nullable=False, default=dict)

    # passive_deletes=True lets the DB ON DELETE CASCADE handle widget removal
    # when a dashboard is deleted, instead of SQLAlchemy nullifying dashboard_id.
    dashboard = relationship(
        "Dashboard",
        backref=backref("widgets", passive_deletes=True)
    )

    __table_args__ = (
        CheckConstraint("width >= 1 AND width <= 4", name="ck_widgets_width"),
        CheckConstraint("height >= 1 AND height <= 3", name="ck_widgets_height"),
        CheckConstraint("position_x >= 0", name="ck_widgets_position_x"),
        CheckConstraint("position_y >= 0", name="ck_widgets_position_y"),
        UniqueConstraint("user_id", "client_id", name="uq_widgets_user_client"),
    )

    def __repr__(self) -> str:
        """String representation of the dashboard widget."""
        return f"<DashboardWidget {self.widget_type.value} '{self.title}'>"
