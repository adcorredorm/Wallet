"""
Tests that widget mutations cascade updated_at to the parent dashboard.

These are integration-style tests that use real DB fixtures to verify
the `_touch_dashboard` side-effect in DashboardCrudService.
"""

import time
import pytest


def test_create_widget_cascades_updated_at(app, make_dashboard):
    """Creating a widget must bump the parent dashboard's updated_at."""
    from app.extensions import db
    from app.services.dashboard_crud import DashboardCrudService
    from app.schemas.dashboard_crud import WidgetCreate

    svc = DashboardCrudService()
    dashboard = make_dashboard()
    original_ts = dashboard.updated_at

    time.sleep(0.02)

    svc.create_widget(dashboard.id, user_id=None, data=WidgetCreate(
        widget_type="line",
        title="Test Widget",
        position_x=0, position_y=0,
        width=4, height=2,
    ))

    db.session.refresh(dashboard)
    assert dashboard.updated_at > original_ts


def test_update_widget_cascades_updated_at(app, make_dashboard, make_widget):
    """Updating a widget must bump the parent dashboard's updated_at."""
    from app.extensions import db
    from app.services.dashboard_crud import DashboardCrudService
    from app.schemas.dashboard_crud import WidgetUpdate

    svc = DashboardCrudService()
    dashboard = make_dashboard()
    widget = make_widget(dashboard_id=dashboard.id)
    original_ts = dashboard.updated_at

    time.sleep(0.02)

    svc.update_widget(dashboard.id, widget.id, user_id=None, data=WidgetUpdate(width=3))

    db.session.refresh(dashboard)
    assert dashboard.updated_at > original_ts


def test_delete_widget_cascades_updated_at(app, make_dashboard, make_widget):
    """Deleting a widget must bump the parent dashboard's updated_at."""
    from app.extensions import db
    from app.services.dashboard_crud import DashboardCrudService

    svc = DashboardCrudService()
    dashboard = make_dashboard()
    widget = make_widget(dashboard_id=dashboard.id)
    original_ts = dashboard.updated_at

    time.sleep(0.02)

    svc.delete_widget(dashboard.id, widget.id, user_id=None)

    db.session.refresh(dashboard)
    assert dashboard.updated_at > original_ts
