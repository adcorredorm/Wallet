"""
Dashboard repository for CRUD configuration data.

Dashboard and DashboardWidget records are owned by users. All collection
queries are scoped to user_id. The widget operations use dashboard_id
(which is already user-scoped through the dashboard lookup) rather than
filtering directly by user_id.
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

    def get_all_ordered(
        self, user_id: UUID, updated_since: datetime | None = None
    ) -> list[Dashboard]:
        """Return dashboards for a user ordered by sort_order, optionally filtered by
        updated_at.

        Args:
            user_id: Owner's UUID.
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all dashboards for the user.

        Returns:
            List of Dashboard instances ordered by sort_order ascending.
        """
        query = (
            db.select(Dashboard)
            .where(Dashboard.user_id == user_id)
            .order_by(Dashboard.sort_order.asc())
        )
        if updated_since is not None:
            query = query.where(Dashboard.updated_at >= updated_since)
        return db.session.execute(query).scalars().all()

    def get_default(self, user_id: UUID) -> Optional[Dashboard]:
        """Return the dashboard marked as default for a user, if any.

        Args:
            user_id: Owner's UUID.

        Returns:
            Default Dashboard instance or None.
        """
        return (
            db.session.execute(
                db.select(Dashboard).where(
                    Dashboard.user_id == user_id,
                    Dashboard.is_default.is_(True),
                )
            )
            .scalars()
            .one_or_none()
        )

    def get_max_sort_order(self, user_id: UUID) -> int:
        """Return current max sort_order for a user's dashboards, or -1 if none exist.

        Args:
            user_id: Owner's UUID.

        Returns:
            Maximum sort_order value or -1.
        """
        result = db.session.execute(
            sa.select(sa.func.max(Dashboard.sort_order)).where(
                Dashboard.user_id == user_id
            )
        ).scalar_one_or_none()
        return result if result is not None else -1

    def count_all(self, user_id: UUID) -> int:
        """Count total number of dashboards for a user.

        Args:
            user_id: Owner's UUID.

        Returns:
            Number of dashboards owned by the user.
        """
        return db.session.execute(
            sa.select(sa.func.count())
            .select_from(Dashboard)
            .where(Dashboard.user_id == user_id)
        ).scalar_one()

    def get_widget(self, widget_id: UUID) -> Optional[DashboardWidget]:
        """Get a single DashboardWidget by ID.

        Ownership is validated by the caller via the parent dashboard's user_id.

        Args:
            widget_id: Widget UUID.

        Returns:
            DashboardWidget or None.
        """
        return db.session.get(DashboardWidget, widget_id)

    def get_widget_by_client_id(
        self, client_id: str, user_id: UUID
    ) -> Optional[DashboardWidget]:
        """Get a DashboardWidget by its client_id idempotency key, scoped to a user
        via the parent dashboard's user_id.

        Args:
            client_id: Client-generated idempotency key.
            user_id: Owner's UUID.

        Returns:
            DashboardWidget or None.
        """
        return (
            db.session.execute(
                db.select(DashboardWidget)
                .join(Dashboard, DashboardWidget.dashboard_id == Dashboard.id)
                .where(
                    DashboardWidget.client_id == client_id,
                    Dashboard.user_id == user_id,
                )
            )
            .scalars()
            .one_or_none()
        )

    def get_widgets_for_dashboard(self, dashboard_id: UUID) -> list[DashboardWidget]:
        """Return all widgets for a dashboard ordered by position.

        Args:
            dashboard_id: Dashboard UUID (already user-scoped by caller).

        Returns:
            List of DashboardWidget instances.
        """
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
        """Count widgets in a specific dashboard.

        Args:
            dashboard_id: Dashboard UUID.

        Returns:
            Number of widgets in the dashboard.
        """
        return db.session.execute(
            sa.select(sa.func.count())
            .select_from(DashboardWidget)
            .where(DashboardWidget.dashboard_id == dashboard_id)
        ).scalar_one()

    def create_widget(self, **kwargs) -> DashboardWidget:
        """Persist a new DashboardWidget.

        Args:
            **kwargs: Widget field values.

        Returns:
            Created DashboardWidget instance.
        """
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

        Args:
            widget: DashboardWidget instance to update.
            **kwargs: Fields to update.

        Returns:
            Updated DashboardWidget instance.
        """
        for key, value in kwargs.items():
            setattr(widget, key, value)
        db.session.commit()
        db.session.refresh(widget)
        return widget

    def delete_widget(self, widget: DashboardWidget) -> None:
        """Delete a DashboardWidget.

        Args:
            widget: DashboardWidget instance to delete.
        """
        db.session.delete(widget)
        db.session.commit()

    def unset_default(self, user_id: UUID) -> None:
        """Clear is_default on all dashboards for a user (call before setting a new
        default).

        Args:
            user_id: Owner's UUID. Only affects dashboards owned by this user.
        """
        db.session.execute(
            sa.update(Dashboard)
            .where(Dashboard.user_id == user_id)
            .values(is_default=False)
        )
        db.session.commit()
