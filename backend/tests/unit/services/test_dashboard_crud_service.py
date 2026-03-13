"""
Unit tests for DashboardCrudService.

These tests focus on business logic validation using mocked repositories.
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

from app.services.dashboard_crud import DashboardCrudService, MAX_DASHBOARDS, MAX_WIDGETS_PER_DASHBOARD
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget, WidgetType
from app.schemas.dashboard_crud import (
    DashboardCreate,
    DashboardUpdate,
    WidgetCreate,
    WidgetUpdate,
    WidgetConfig,
)
from app.utils.exceptions import NotFoundError, BusinessRuleError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo():
    """Create a mocked DashboardRepository."""
    with patch("app.services.dashboard_crud.DashboardRepository") as mock:
        yield mock.return_value


@pytest.fixture
def service(mock_repo):
    """Create DashboardCrudService instance with mocked repository."""
    svc = DashboardCrudService()
    svc.repo = mock_repo
    return svc


@pytest.fixture
def sample_dashboard():
    """Create a sample Dashboard mock for testing.

    Uses MagicMock without spec= to avoid triggering Flask-SQLAlchemy's
    query descriptor which requires an app context during Mock spec introspection.
    """
    d = MagicMock()
    d.id = uuid4()
    d.name = "My Dashboard"
    d.description = "Test description"
    d.display_currency = "USD"
    d.layout_columns = 2
    d.is_default = False
    d.sort_order = 0
    d.client_id = None
    return d


@pytest.fixture
def sample_widget(sample_dashboard):
    """Create a sample DashboardWidget mock for testing.

    Uses MagicMock without spec= for the same reason as sample_dashboard.
    """
    w = MagicMock()
    w.id = uuid4()
    w.dashboard_id = sample_dashboard.id
    w.widget_type = WidgetType.LINE
    w.title = "Revenue"
    w.position_x = 0
    w.position_y = 0
    w.width = 1
    w.height = 1
    w.config = {}
    w.client_id = None
    return w


# ---------------------------------------------------------------------------
# TestListDashboards
# ---------------------------------------------------------------------------


class TestListDashboards:
    """Tests for list_dashboards method."""

    def test_returns_ordered_list(self, service, mock_repo, sample_dashboard):
        """Should return dashboards in sort_order from repository."""
        mock_repo.get_all_ordered.return_value = [sample_dashboard]

        result = service.list_dashboards()

        mock_repo.get_all_ordered.assert_called_once()
        assert result == [sample_dashboard]

    def test_returns_empty_list_when_none(self, service, mock_repo):
        """Should return empty list when no dashboards exist."""
        mock_repo.get_all_ordered.return_value = []

        result = service.list_dashboards()

        assert result == []


# ---------------------------------------------------------------------------
# TestCreateDashboard
# ---------------------------------------------------------------------------


class TestCreateDashboard:
    """Tests for create_dashboard method."""

    def _make_data(self, **kwargs) -> DashboardCreate:
        defaults = dict(
            name="Test Dashboard",
            display_currency="USD",
            is_default=False,
            sort_order=None,
            client_id=None,
            description=None,
            layout_columns=2,
        )
        defaults.update(kwargs)
        return DashboardCreate(**defaults)

    def test_creates_successfully(self, service, mock_repo, sample_dashboard):
        """Should create a new dashboard and return (dashboard, True)."""
        mock_repo.get_by_client_id.return_value = None
        mock_repo.count_all.return_value = 0
        mock_repo.get_max_sort_order.return_value = 0
        mock_repo.create.return_value = sample_dashboard

        data = self._make_data()
        result, created = service.create_dashboard(data)

        assert result is sample_dashboard
        assert created is True
        mock_repo.create.assert_called_once()

    def test_auto_assigns_sort_order(self, service, mock_repo, sample_dashboard):
        """Should set sort_order = max+1 when not provided."""
        mock_repo.count_all.return_value = 2
        mock_repo.get_max_sort_order.return_value = 5
        mock_repo.create.return_value = sample_dashboard

        data = self._make_data(sort_order=None)
        service.create_dashboard(data)

        call_kwargs = mock_repo.create.call_args.kwargs
        assert call_kwargs["sort_order"] == 6  # max(5) + 1

    def test_uses_provided_sort_order(self, service, mock_repo, sample_dashboard):
        """Should use sort_order from data when explicitly provided."""
        mock_repo.count_all.return_value = 1
        mock_repo.create.return_value = sample_dashboard

        data = self._make_data(sort_order=99)
        service.create_dashboard(data)

        call_kwargs = mock_repo.create.call_args.kwargs
        assert call_kwargs["sort_order"] == 99
        mock_repo.get_max_sort_order.assert_not_called()

    def test_idempotency_returns_existing(self, service, mock_repo, sample_dashboard):
        """Should return existing dashboard with created=False when client_id matches."""
        sample_dashboard.client_id = "cli-abc"
        mock_repo.get_by_client_id.return_value = sample_dashboard

        data = self._make_data(client_id="cli-abc")
        result, created = service.create_dashboard(data)

        assert result is sample_dashboard
        assert created is False
        mock_repo.create.assert_not_called()

    def test_raises_when_limit_reached(self, service, mock_repo):
        """Should raise BusinessRuleError when MAX_DASHBOARDS would be exceeded."""
        mock_repo.get_by_client_id.return_value = None
        mock_repo.count_all.return_value = MAX_DASHBOARDS  # exactly at limit

        data = self._make_data()
        with pytest.raises(BusinessRuleError):
            service.create_dashboard(data)

        mock_repo.create.assert_not_called()

    def test_is_default_unsets_previous(self, service, mock_repo, sample_dashboard):
        """Should call unset_default before creating when is_default=True."""
        mock_repo.count_all.return_value = 0
        mock_repo.get_max_sort_order.return_value = 0
        mock_repo.create.return_value = sample_dashboard

        data = self._make_data(is_default=True)
        service.create_dashboard(data)

        mock_repo.unset_default.assert_called_once()

    def test_non_default_does_not_unset(self, service, mock_repo, sample_dashboard):
        """Should NOT call unset_default when is_default=False."""
        mock_repo.count_all.return_value = 0
        mock_repo.get_max_sort_order.return_value = 0
        mock_repo.create.return_value = sample_dashboard

        data = self._make_data(is_default=False)
        service.create_dashboard(data)

        mock_repo.unset_default.assert_not_called()


# ---------------------------------------------------------------------------
# TestGetDashboard
# ---------------------------------------------------------------------------


class TestGetDashboard:
    """Tests for get_dashboard method."""

    def test_returns_dashboard(self, service, mock_repo, sample_dashboard):
        """Should return the dashboard when found."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard

        result = service.get_dashboard(sample_dashboard.id)

        mock_repo.get_by_id_or_fail.assert_called_once_with(sample_dashboard.id)
        assert result is sample_dashboard

    def test_raises_if_not_found(self, service, mock_repo):
        """Should raise NotFoundError when dashboard does not exist."""
        mock_repo.get_by_id_or_fail.side_effect = NotFoundError("Dashboard", str(uuid4()))

        with pytest.raises(NotFoundError):
            service.get_dashboard(uuid4())


# ---------------------------------------------------------------------------
# TestUpdateDashboard
# ---------------------------------------------------------------------------


class TestUpdateDashboard:
    """Tests for update_dashboard method."""

    def test_updates_name(self, service, mock_repo, sample_dashboard):
        """Should call repo.update with the provided name."""
        updated = MagicMock()
        updated.name = "Renamed"
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.update.return_value = updated

        data = DashboardUpdate(name="Renamed")
        result = service.update_dashboard(sample_dashboard.id, data)

        assert result is updated
        mock_repo.update.assert_called_once()
        call_kwargs = mock_repo.update.call_args.kwargs
        assert call_kwargs["name"] == "Renamed"

    def test_is_default_true_unsets_previous(self, service, mock_repo, sample_dashboard):
        """Should call unset_default before updating when is_default=True."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.update.return_value = sample_dashboard

        data = DashboardUpdate(is_default=True)
        service.update_dashboard(sample_dashboard.id, data)

        mock_repo.unset_default.assert_called_once()

    def test_is_default_false_does_not_unset(self, service, mock_repo, sample_dashboard):
        """Should NOT call unset_default when is_default is not True."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.update.return_value = sample_dashboard

        data = DashboardUpdate(name="Keep name")
        service.update_dashboard(sample_dashboard.id, data)

        mock_repo.unset_default.assert_not_called()

    def test_raises_if_not_found(self, service, mock_repo):
        """Should raise NotFoundError when dashboard does not exist."""
        mock_repo.get_by_id_or_fail.side_effect = NotFoundError("Dashboard", str(uuid4()))

        with pytest.raises(NotFoundError):
            service.update_dashboard(uuid4(), DashboardUpdate(name="X"))


# ---------------------------------------------------------------------------
# TestDeleteDashboard
# ---------------------------------------------------------------------------


class TestDeleteDashboard:
    """Tests for delete_dashboard method."""

    def test_deletes_successfully(self, service, mock_repo, sample_dashboard):
        """Should call repo.delete with the found dashboard."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard

        service.delete_dashboard(sample_dashboard.id)

        mock_repo.delete.assert_called_once_with(sample_dashboard)

    def test_raises_if_not_found(self, service, mock_repo):
        """Should raise NotFoundError when dashboard does not exist."""
        mock_repo.get_by_id_or_fail.side_effect = NotFoundError("Dashboard", str(uuid4()))

        with pytest.raises(NotFoundError):
            service.delete_dashboard(uuid4())

        mock_repo.delete.assert_not_called()


# ---------------------------------------------------------------------------
# TestListWidgets
# ---------------------------------------------------------------------------


class TestListWidgets:
    """Tests for list_widgets method."""

    def test_returns_widgets_for_existing_dashboard(
        self, service, mock_repo, sample_dashboard, sample_widget
    ):
        """Should return widgets after confirming dashboard exists."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widgets_for_dashboard.return_value = [sample_widget]

        result = service.list_widgets(sample_dashboard.id)

        mock_repo.get_by_id_or_fail.assert_called_once_with(sample_dashboard.id)
        mock_repo.get_widgets_for_dashboard.assert_called_once_with(sample_dashboard.id)
        assert result == [sample_widget]

    def test_raises_if_dashboard_not_found(self, service, mock_repo):
        """Should raise NotFoundError when dashboard does not exist."""
        mock_repo.get_by_id_or_fail.side_effect = NotFoundError("Dashboard", str(uuid4()))

        with pytest.raises(NotFoundError):
            service.list_widgets(uuid4())

        mock_repo.get_widgets_for_dashboard.assert_not_called()


# ---------------------------------------------------------------------------
# TestCreateWidget
# ---------------------------------------------------------------------------


class TestCreateWidget:
    """Tests for create_widget method."""

    def _make_widget_data(self, **kwargs) -> WidgetCreate:
        defaults = dict(
            widget_type="line",
            title="My Widget",
            position_x=0,
            position_y=0,
            width=1,
            height=1,
            client_id=None,
            config=WidgetConfig(),
        )
        defaults.update(kwargs)
        return WidgetCreate(**defaults)

    def test_creates_successfully(self, service, mock_repo, sample_dashboard, sample_widget):
        """Should create a widget and return (widget, True)."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget_by_client_id.return_value = None
        mock_repo.count_widgets_for_dashboard.return_value = 0
        mock_repo.create_widget.return_value = sample_widget

        data = self._make_widget_data()
        result, created = service.create_widget(sample_dashboard.id, data)

        assert result is sample_widget
        assert created is True
        mock_repo.create_widget.assert_called_once()

    def test_idempotency_returns_existing_widget(
        self, service, mock_repo, sample_dashboard, sample_widget
    ):
        """Should return existing widget with created=False when client_id matches."""
        sample_widget.client_id = "wgt-xyz"
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget_by_client_id.return_value = sample_widget

        data = self._make_widget_data(client_id="wgt-xyz")
        result, created = service.create_widget(sample_dashboard.id, data)

        assert result is sample_widget
        assert created is False
        mock_repo.create_widget.assert_not_called()

    def test_raises_when_widget_limit_reached(self, service, mock_repo, sample_dashboard):
        """Should raise BusinessRuleError when MAX_WIDGETS_PER_DASHBOARD would be exceeded."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget_by_client_id.return_value = None
        mock_repo.count_widgets_for_dashboard.return_value = MAX_WIDGETS_PER_DASHBOARD

        data = self._make_widget_data()
        with pytest.raises(BusinessRuleError):
            service.create_widget(sample_dashboard.id, data)

        mock_repo.create_widget.assert_not_called()

    def test_raises_if_dashboard_not_found(self, service, mock_repo):
        """Should raise NotFoundError when dashboard does not exist."""
        mock_repo.get_by_id_or_fail.side_effect = NotFoundError("Dashboard", str(uuid4()))

        data = self._make_widget_data()
        with pytest.raises(NotFoundError):
            service.create_widget(uuid4(), data)

        mock_repo.create_widget.assert_not_called()


# ---------------------------------------------------------------------------
# TestUpdateWidget
# ---------------------------------------------------------------------------


class TestUpdateWidget:
    """Tests for update_widget method."""

    def test_updates_title(self, service, mock_repo, sample_dashboard, sample_widget):
        """Should call repo.update_widget with the new title."""
        updated = MagicMock()
        updated.title = "New Title"
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget.return_value = sample_widget
        mock_repo.update_widget.return_value = updated

        data = WidgetUpdate(title="New Title")
        result = service.update_widget(sample_dashboard.id, sample_widget.id, data)

        assert result is updated
        mock_repo.update_widget.assert_called_once()
        call_kwargs = mock_repo.update_widget.call_args.kwargs
        assert call_kwargs["title"] == "New Title"

    def test_updates_position_x_zero(self, service, mock_repo, sample_dashboard, sample_widget):
        """Should correctly pass position_x=0 — falsy value must not be skipped."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget.return_value = sample_widget
        mock_repo.update_widget.return_value = sample_widget

        data = WidgetUpdate(position_x=0)
        service.update_widget(sample_dashboard.id, sample_widget.id, data)

        call_kwargs = mock_repo.update_widget.call_args.kwargs
        assert "position_x" in call_kwargs
        assert call_kwargs["position_x"] == 0

    def test_raises_if_widget_belongs_to_different_dashboard(
        self, service, mock_repo, sample_dashboard, sample_widget
    ):
        """Should raise NotFoundError when widget belongs to a different dashboard."""
        other_dashboard_id = uuid4()
        sample_widget.dashboard_id = other_dashboard_id  # mismatched owner

        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget.return_value = sample_widget

        data = WidgetUpdate(title="Intruder")
        with pytest.raises(NotFoundError):
            service.update_widget(sample_dashboard.id, sample_widget.id, data)

        mock_repo.update_widget.assert_not_called()

    def test_raises_if_widget_not_found(self, service, mock_repo, sample_dashboard):
        """Should raise NotFoundError when widget does not exist."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget.return_value = None  # not found

        data = WidgetUpdate(title="Ghost")
        with pytest.raises(NotFoundError):
            service.update_widget(sample_dashboard.id, uuid4(), data)

        mock_repo.update_widget.assert_not_called()


# ---------------------------------------------------------------------------
# TestDeleteWidget
# ---------------------------------------------------------------------------


class TestDeleteWidget:
    """Tests for delete_widget method."""

    def test_deletes_successfully(self, service, mock_repo, sample_dashboard, sample_widget):
        """Should call repo.delete_widget when dashboard and widget are valid."""
        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget.return_value = sample_widget

        service.delete_widget(sample_dashboard.id, sample_widget.id)

        mock_repo.delete_widget.assert_called_once_with(sample_widget)

    def test_raises_if_widget_owned_by_other_dashboard(
        self, service, mock_repo, sample_dashboard, sample_widget
    ):
        """Should raise NotFoundError when widget belongs to a different dashboard."""
        sample_widget.dashboard_id = uuid4()  # different owner

        mock_repo.get_by_id_or_fail.return_value = sample_dashboard
        mock_repo.get_widget.return_value = sample_widget

        with pytest.raises(NotFoundError):
            service.delete_widget(sample_dashboard.id, sample_widget.id)

        mock_repo.delete_widget.assert_not_called()


# ---------------------------------------------------------------------------
# TestWidgetConfigValidation
# ---------------------------------------------------------------------------


class TestWidgetConfigValidation:
    """Tests for WidgetConfig Pydantic schema validation."""

    def test_valid_config_accepted(self):
        """A well-formed WidgetConfig should instantiate without error."""
        from app.schemas.dashboard_crud import WidgetConfig, TimeRangeConfig, FiltersConfig
        config = WidgetConfig(
            time_range=TimeRangeConfig(type="dynamic", value="this_month"),
            filters=FiltersConfig(type="expense"),
            granularity="month",
            group_by="category",
            aggregation="sum",
        )
        assert config.granularity == "month"
        assert config.group_by == "category"

    def test_extra_fields_allowed(self):
        """WidgetConfig has extra='allow' so unknown fields pass through."""
        from app.schemas.dashboard_crud import WidgetConfig
        config = WidgetConfig(unknown_future_field="value")
        assert config.unknown_future_field == "value"  # type: ignore[attr-defined]

    def test_invalid_widget_type_rejected(self):
        """WidgetCreate should reject unknown widget_type strings."""
        from app.schemas.dashboard_crud import WidgetCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            WidgetCreate(widget_type="radar", title="Bad type")

    def test_valid_widget_type_accepted(self):
        """WidgetCreate should accept all five valid widget types."""
        from app.schemas.dashboard_crud import WidgetCreate
        for wtype in ("line", "pie", "bar", "stacked_bar", "number"):
            w = WidgetCreate(widget_type=wtype, title="Test")
            assert w.widget_type == wtype

    def test_empty_config_uses_defaults(self):
        """WidgetCreate without explicit config should use an empty WidgetConfig."""
        from app.schemas.dashboard_crud import WidgetCreate, WidgetConfig
        w = WidgetCreate(widget_type="bar", title="No config")
        assert isinstance(w.config, WidgetConfig)
        assert w.config.granularity is None
