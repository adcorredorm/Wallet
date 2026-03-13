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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class WidgetType(enum.Enum):
    """Supported chart / display types for a widget."""

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
    __table_args__ = (
        CheckConstraint("width >= 1 AND width <= 4", name="ck_widgets_width"),
        CheckConstraint("height >= 1 AND height <= 3", name="ck_widgets_height"),
        CheckConstraint("position_x >= 0", name="ck_widgets_position_x"),
        CheckConstraint("position_y >= 0", name="ck_widgets_position_y"),
    )

    dashboard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    widget_type = Column(Enum(WidgetType), nullable=False)
    title = Column(String(100), nullable=False)
    position_x = Column(Integer, nullable=False, default=0)
    position_y = Column(Integer, nullable=False, default=0)
    width = Column(Integer, nullable=False, default=1)
    height = Column(Integer, nullable=False, default=1)
    config = Column(JSONB, nullable=False, default=dict)

    dashboard = relationship("Dashboard", backref="widgets")
