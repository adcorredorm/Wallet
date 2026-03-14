"""
Dashboard repository for CRUD configuration data.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget
from app.repositories.base import BaseRepository


class DashboardRepository(BaseRepository[Dashboard]):
    """Repository for Dashboard entity with dashboard-specific queries."""

    def __init__(self) -> None:
        super().__init__(Dashboard)

    def get_all_ordered(self, updated_since: datetime | None = None) -> list[Dashboard]:
        """Return dashboards ordered by sort_order, optionally filtered by updated_at.

        Args:
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all dashboards.

        Returns:
            List of Dashboard instances ordered by sort_order ascending.
        """
        query = db.select(Dashboard).order_by(Dashboard.sort_order.asc())
        if updated_since is not None:
            query = query.where(Dashboard.updated_at >= updated_since)
        return db.session.execute(query).scalars().all()

    def get_default(self) -> Optional[Dashboard]:
        """Return the dashboard marked as default, if any."""
        return (
            db.session.execute(
                db.select(Dashboard).where(Dashboard.is_default.is_(True))
            )
            .scalars()
            .one_or_none()
        )

    def get_max_sort_order(self) -> int:
        """Return current max sort_order, or -1 if no dashboards exist."""
        result = db.session.execute(
            sa.select(sa.func.max(Dashboard.sort_order))
        ).scalar_one_or_none()
        return result if result is not None else -1

    def count_all(self) -> int:
        """Count total number of dashboards."""
        return db.session.execute(
            sa.select(sa.func.count()).select_from(Dashboard)
        ).scalar_one()

    def get_widget(self, widget_id: UUID) -> Optional[DashboardWidget]:
        """Get a single DashboardWidget by ID."""
        return db.session.get(DashboardWidget, widget_id)

    def get_widget_by_client_id(self, client_id: str) -> Optional[DashboardWidget]:
        """Get a DashboardWidget by its client_id idempotency key."""
        return (
            db.session.execute(
                db.select(DashboardWidget).where(DashboardWidget.client_id == client_id)
            )
            .scalars()
            .one_or_none()
        )

    def get_widgets_for_dashboard(self, dashboard_id: UUID) -> list[DashboardWidget]:
        """Return all widgets for a dashboard ordered by position."""
        return (
            db.session.execute(
                db.select(DashboardWidget)
                .where(DashboardWidget.dashboard_id == dashboard_id)
                .order_by(
                    DashboardWidget.position_y.asc(),
                    DashboardWidget.position_x.asc(),
                )
            )
            .scalars()
            .all()
        )

    def count_widgets_for_dashboard(self, dashboard_id: UUID) -> int:
        """Count widgets in a specific dashboard."""
        return db.session.execute(
            sa.select(sa.func.count())
            .select_from(DashboardWidget)
            .where(DashboardWidget.dashboard_id == dashboard_id)
        ).scalar_one()

    def create_widget(self, **kwargs) -> DashboardWidget:
        """Persist a new DashboardWidget."""
        widget = DashboardWidget(**kwargs)
        db.session.add(widget)
        db.session.commit()
        db.session.refresh(widget)
        return widget

    def update_widget(self, widget: DashboardWidget, **kwargs) -> DashboardWidget:
        """
        Update an existing DashboardWidget.

        Unlike BaseRepository.update(), this method unconditionally applies all
        provided keys including falsy values (0, False). The service layer is
        responsible for only passing fields that should be changed.
        """
        for key, value in kwargs.items():
            setattr(widget, key, value)
        db.session.commit()
        db.session.refresh(widget)
        return widget

    def delete_widget(self, widget: DashboardWidget) -> None:
        """Delete a DashboardWidget."""
        db.session.delete(widget)
        db.session.commit()

    def unset_default(self) -> None:
        """Clear is_default on all dashboards (call before setting a new default)."""
        db.session.execute(
            sa.update(Dashboard).values(is_default=False)
        )
        db.session.commit()
