"""
DashboardCrudService: business logic for Dashboard and DashboardWidget CRUD.

This service persists configuration only — it never computes analytics.
Every method that queries user-owned data accepts a user_id parameter.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

import sqlalchemy as sa

from app.extensions import db
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget, WidgetType
from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard_crud import DashboardCreate, DashboardUpdate, WidgetCreate, WidgetUpdate
from app.utils.exceptions import NotFoundError, BusinessRuleError

MAX_DASHBOARDS = 10
MAX_WIDGETS_PER_DASHBOARD = 12


class DashboardCrudService:
    """
    Business logic for Dashboard and DashboardWidget CRUD.

    Enforces:
    - Maximum 10 dashboards per user.
    - Maximum 12 widgets per dashboard.
    - Single-default invariant for dashboards (per user).
    - offline_id idempotency for dashboards and widgets.
    - Automatic sort_order assignment when omitted.
    """

    def __init__(self) -> None:
        self.repo = DashboardRepository()

    # ------------------------------------------------------------------
    # Dashboard CRUD
    # ------------------------------------------------------------------

    def list_dashboards(
        self, user_id: UUID, updated_since: datetime | None = None
    ) -> list[Dashboard]:
        """Return all dashboards for a user ordered by sort_order.

        Args:
            user_id: Owner's UUID.
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all dashboards for the user.

        Returns:
            List of Dashboard instances ordered by sort_order ascending.
        """
        return self.repo.get_all_ordered(user_id=user_id, updated_since=updated_since)

    def get_dashboard(self, dashboard_id: UUID, user_id: UUID) -> Dashboard:
        """Return a single dashboard by ID or raise NotFoundError.

        Args:
            dashboard_id: Dashboard UUID.
            user_id: Owner's UUID.

        Returns:
            Dashboard instance.

        Raises:
            NotFoundError: If not found or not owned by this user.
        """
        return self.repo.get_by_id_or_fail(dashboard_id, user_id)

    def create_dashboard(
        self, user_id: UUID, data: DashboardCreate
    ) -> tuple[Dashboard, bool]:
        """
        Create a new dashboard for a user. Returns (instance, created: bool).
        created=False means idempotency hit (existing record returned).

        Args:
            user_id: Owner's UUID.
            data: Dashboard creation payload.

        Returns:
            Tuple of (Dashboard, created_flag).

        Raises:
            BusinessRuleError: If dashboard limit (10) per user would be exceeded.
        """
        if data.offline_id:
            existing = self.repo.get_by_offline_id(data.offline_id, user_id)
            if existing:
                return existing, False

        if self.repo.count_all(user_id) >= MAX_DASHBOARDS:
            raise BusinessRuleError(
                f"No se pueden crear más de {MAX_DASHBOARDS} dashboards."
            )

        sort_order = data.sort_order
        if sort_order is None:
            sort_order = self.repo.get_max_sort_order(user_id) + 1

        if data.is_default:
            self.repo.unset_default(user_id)

        dashboard = self.repo.create(
            user_id=user_id,
            name=data.name,
            description=data.description,
            display_currency=data.display_currency,
            layout_columns=data.layout_columns,
            is_default=data.is_default,
            sort_order=sort_order,
            offline_id=data.offline_id,
        )
        return dashboard, True

    def update_dashboard(
        self, dashboard_id: UUID, user_id: UUID, data: DashboardUpdate
    ) -> Dashboard:
        """Update dashboard metadata. Raises NotFoundError if not found.

        Args:
            dashboard_id: Dashboard UUID.
            user_id: Owner's UUID.
            data: Dashboard update payload.

        Returns:
            Updated Dashboard instance.
        """
        dashboard = self.repo.get_by_id_or_fail(dashboard_id, user_id)

        if data.is_default is True:
            self.repo.unset_default(user_id)

        update_fields = data.model_dump(exclude_unset=True)
        return self.repo.update(dashboard, **update_fields)

    def delete_dashboard(self, dashboard_id: UUID, user_id: UUID) -> None:
        """Delete a dashboard and cascade widgets. Raises NotFoundError if not found.

        Args:
            dashboard_id: Dashboard UUID.
            user_id: Owner's UUID.
        """
        dashboard = self.repo.get_by_id_or_fail(dashboard_id, user_id)
        self.repo.delete(dashboard)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _touch_dashboard(self, dashboard_id: UUID) -> None:
        """Update Dashboard.updated_at to now after a widget mutation.

        Called after every widget create/update/delete so the incremental sync
        cursor detects widget changes via the parent dashboard timestamp.

        Args:
            dashboard_id: Primary key of the dashboard to touch.
        """
        db.session.execute(
            sa.update(Dashboard)
            .where(Dashboard.id == dashboard_id)
            .values(updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
        )
        db.session.commit()

    # ------------------------------------------------------------------
    # Widget CRUD
    # ------------------------------------------------------------------

    def list_widgets(
        self, dashboard_id: UUID, user_id: UUID
    ) -> list[DashboardWidget]:
        """Return all widgets for a dashboard. Raises NotFoundError if dashboard not found.

        Args:
            dashboard_id: Dashboard UUID.
            user_id: Owner's UUID.

        Returns:
            List of DashboardWidget instances.
        """
        self.repo.get_by_id_or_fail(dashboard_id, user_id)
        return self.repo.get_widgets_for_dashboard(dashboard_id)

    def create_widget(
        self, dashboard_id: UUID, user_id: UUID, data: WidgetCreate
    ) -> tuple[DashboardWidget, bool]:
        """
        Add a widget to a dashboard. Returns (instance, created: bool).

        Args:
            dashboard_id: Dashboard UUID.
            user_id: Owner's UUID.
            data: Widget creation payload.

        Returns:
            Tuple of (DashboardWidget, created_flag).

        Raises:
            NotFoundError: If the dashboard does not exist or is not owned by
                this user.
            BusinessRuleError: If widget limit (12) would be exceeded.
        """
        self.repo.get_by_id_or_fail(dashboard_id, user_id)

        if data.offline_id:
            existing_widget = self.repo.get_widget_by_offline_id(
                data.offline_id, user_id
            )
            if existing_widget:
                return existing_widget, False

        if self.repo.count_widgets_for_dashboard(dashboard_id) >= MAX_WIDGETS_PER_DASHBOARD:
            raise BusinessRuleError(
                f"No se pueden agregar más de {MAX_WIDGETS_PER_DASHBOARD} "
                "widgets por dashboard."
            )

        widget_type_enum = WidgetType(data.widget_type)
        config_dict = data.config.model_dump(exclude_none=True) if data.config else {}

        widget = self.repo.create_widget(
            dashboard_id=dashboard_id,
            user_id=user_id,
            widget_type=widget_type_enum,
            title=data.title,
            position_x=data.position_x,
            position_y=data.position_y,
            width=data.width,
            height=data.height,
            config=config_dict,
            offline_id=data.offline_id,
        )
        self._touch_dashboard(dashboard_id)
        return widget, True

    def update_widget(
        self,
        dashboard_id: UUID,
        widget_id: UUID,
        user_id: UUID,
        data: WidgetUpdate,
    ) -> DashboardWidget:
        """
        Update a widget's config or layout.

        Args:
            dashboard_id: Dashboard UUID.
            widget_id: Widget UUID.
            user_id: Owner's UUID.
            data: Widget update payload.

        Returns:
            Updated DashboardWidget instance.

        Raises:
            NotFoundError: If the dashboard or widget does not exist, or widget
                does not belong to the specified dashboard.
        """
        self.repo.get_by_id_or_fail(dashboard_id, user_id)
        widget = self.repo.get_widget(widget_id)
        if not widget or str(widget.dashboard_id) != str(dashboard_id):
            raise NotFoundError("DashboardWidget", str(widget_id))

        update_fields: dict = {}
        if data.widget_type is not None:
            update_fields["widget_type"] = WidgetType(data.widget_type)
        if data.title is not None:
            update_fields["title"] = data.title
        if data.position_x is not None:
            update_fields["position_x"] = data.position_x
        if data.position_y is not None:
            update_fields["position_y"] = data.position_y
        if data.width is not None:
            update_fields["width"] = data.width
        if data.height is not None:
            update_fields["height"] = data.height
        if data.config is not None:
            update_fields["config"] = data.config.model_dump(exclude_none=True)

        updated_widget = self.repo.update_widget(widget, **update_fields)
        self._touch_dashboard(dashboard_id)
        return updated_widget

    def delete_widget(
        self, dashboard_id: UUID, widget_id: UUID, user_id: UUID
    ) -> None:
        """
        Delete a widget from a dashboard.

        Args:
            dashboard_id: Dashboard UUID.
            widget_id: Widget UUID.
            user_id: Owner's UUID.

        Raises:
            NotFoundError: If the dashboard or widget does not exist, or widget
                does not belong to the specified dashboard.
        """
        self.repo.get_by_id_or_fail(dashboard_id, user_id)
        widget = self.repo.get_widget(widget_id)
        if not widget or str(widget.dashboard_id) != str(dashboard_id):
            raise NotFoundError("DashboardWidget", str(widget_id))
        self.repo.delete_widget(widget)
        self._touch_dashboard(dashboard_id)
