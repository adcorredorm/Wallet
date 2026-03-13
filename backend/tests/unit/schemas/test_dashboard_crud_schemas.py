"""
Unit tests for dashboard CRUD Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.dashboard_crud import (
    WidgetConfig,
    WidgetCreate,
    TimeRangeConfig,
    FiltersConfig,
)


class TestWidgetConfigValidation:
    """Tests for WidgetConfig Pydantic schema validation."""

    def test_valid_config_accepted(self):
        """A well-formed WidgetConfig should instantiate without error."""
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
        config = WidgetConfig(unknown_future_field="value")
        assert config.unknown_future_field == "value"  # type: ignore[attr-defined]

    def test_invalid_widget_type_rejected(self):
        """WidgetCreate should reject unknown widget_type strings."""
        with pytest.raises(ValidationError):
            WidgetCreate(widget_type="radar", title="Bad type")

    def test_valid_widget_types_accepted(self):
        """WidgetCreate should accept all five valid widget types."""
        for wtype in ("line", "pie", "bar", "stacked_bar", "number"):
            w = WidgetCreate(widget_type=wtype, title="Test")
            assert w.widget_type == wtype

    def test_empty_config_uses_defaults(self):
        """WidgetCreate without explicit config should use an empty WidgetConfig."""
        w = WidgetCreate(widget_type="bar", title="No config")
        assert isinstance(w.config, WidgetConfig)
        assert w.config.granularity is None
