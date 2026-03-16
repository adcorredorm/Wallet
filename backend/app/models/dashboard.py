"""
Dashboard model for user-defined analytics dashboards.
"""

from sqlalchemy import Column, String, Integer, Boolean, CheckConstraint, UniqueConstraint
from app.models.base import BaseModel


class Dashboard(BaseModel):
    """
    User-defined analytics dashboard.

    A dashboard groups widgets and controls layout width (1-4 columns).
    At most one dashboard may have is_default=True at any time; the service
    layer enforces this invariant.

    Attributes:
        name: Human-readable name (max 100 characters).
        description: Optional longer description (max 500 characters).
        display_currency: ISO 4217 currency code for all widgets in this dashboard.
        layout_columns: Number of grid columns (1–4, default 2).
        is_default: Whether this is the user's default dashboard.
        sort_order: Display order (lower = first).
    """

    __tablename__ = "dashboards"

    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    display_currency = Column(String(10), nullable=False)  # ISO 4217; set to user's primaryCurrency on create
    layout_columns = Column(Integer, nullable=False, default=2)
    is_default = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint(
            "layout_columns >= 1 AND layout_columns <= 4",
            name="ck_dashboards_layout_columns",
        ),
        UniqueConstraint("user_id", "offline_id", name="uq_dashboards_user_offline"),
    )

    def __repr__(self) -> str:
        """String representation of the dashboard."""
        default_marker = " [default]" if self.is_default else ""
        return f"<Dashboard '{self.name}'{default_marker}>"
