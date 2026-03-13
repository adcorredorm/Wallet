"""
Pydantic schemas for Dashboard + DashboardWidget CRUD endpoints.

These schemas do NOT cover analytics — analytics are computed on the frontend.
display_currency lives on Dashboard, not on WidgetConfig.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# WidgetConfig sub-schemas
# ---------------------------------------------------------------------------

class TimeRangeConfig(BaseModel):
    """Time range configuration for a widget."""
    type: Literal["dynamic", "static"] = "dynamic"
    value: Optional[Any] = None  # string preset or {"from": "...", "to": "..."}


class FiltersConfig(BaseModel):
    """Data filters applied when the frontend queries IndexedDB."""
    account_ids: list[str] = Field(default_factory=list)
    category_ids: list[str] = Field(default_factory=list)
    type: Optional[str] = None  # "income" | "expense" | None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None


class WidgetConfig(BaseModel):
    """
    Complete configuration blob stored in DashboardWidget.config (JSONB).

    display_currency is NOT here — it lives on Dashboard and applies to all widgets.
    All fields are optional for forward-compatibility; the frontend applies defaults.
    """
    time_range: Optional[TimeRangeConfig] = None
    filters: Optional[FiltersConfig] = None
    granularity: Optional[str] = None  # "day"|"week"|"month"|"quarter"|"semester"|"year"
    group_by: Optional[str] = None  # "category"|"account"|"type"|"day_of_week"|"none"
    aggregation: Optional[str] = None  # "sum"|"count"|"avg"|"min"|"max"
    category_groups: Optional[dict[str, list[str]]] = None

    model_config = {"extra": "allow"}  # forward-compatibility


# ---------------------------------------------------------------------------
# Dashboard schemas
# ---------------------------------------------------------------------------

class DashboardCreate(BaseModel):
    """Request body for POST /api/v1/dashboards."""
    client_id: Optional[str] = Field(None, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    display_currency: str = Field(..., min_length=3, max_length=10)
    layout_columns: int = Field(2, ge=1, le=4)
    is_default: bool = False
    sort_order: Optional[int] = Field(None, ge=0)


class DashboardUpdate(BaseModel):
    """Request body for PUT /api/v1/dashboards/:id (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    display_currency: Optional[str] = Field(None, min_length=3, max_length=10)
    layout_columns: Optional[int] = Field(None, ge=1, le=4)
    is_default: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)


class DashboardResponse(BaseModel):
    """Serialized Dashboard (without widgets)."""
    id: UUID
    client_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    display_currency: str
    layout_columns: int
    is_default: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Widget schemas
# ---------------------------------------------------------------------------

ALLOWED_WIDGET_TYPES = {"line", "pie", "bar", "stacked_bar", "number"}


class WidgetCreate(BaseModel):
    """Request body for POST /api/v1/dashboards/:id/widgets."""
    client_id: Optional[str] = Field(None, max_length=100)
    widget_type: str = Field(..., description="line|pie|bar|stacked_bar|number")
    title: str = Field(..., min_length=1, max_length=100)
    position_x: int = Field(0, ge=0)
    position_y: int = Field(0, ge=0)
    width: int = Field(1, ge=1, le=4)
    height: int = Field(1, ge=1, le=3)
    config: WidgetConfig = Field(default_factory=WidgetConfig)

    @field_validator("widget_type")
    @classmethod
    def validate_widget_type(cls, v: str) -> str:
        if v not in ALLOWED_WIDGET_TYPES:
            raise ValueError(f"widget_type must be one of {sorted(ALLOWED_WIDGET_TYPES)}")
        return v


class WidgetUpdate(BaseModel):
    """Request body for PUT /api/v1/dashboards/:id/widgets/:wid."""
    widget_type: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    position_x: Optional[int] = Field(None, ge=0)
    position_y: Optional[int] = Field(None, ge=0)
    width: Optional[int] = Field(None, ge=1, le=4)
    height: Optional[int] = Field(None, ge=1, le=3)
    config: Optional[WidgetConfig] = None

    @field_validator("widget_type")
    @classmethod
    def validate_widget_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_WIDGET_TYPES:
            raise ValueError(f"widget_type must be one of {sorted(ALLOWED_WIDGET_TYPES)}")
        return v


class WidgetResponse(BaseModel):
    """Serialized DashboardWidget."""
    id: UUID
    client_id: Optional[str] = None
    dashboard_id: UUID
    widget_type: str
    title: str
    position_x: int
    position_y: int
    width: int
    height: int
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("widget_type", mode="before")
    @classmethod
    def coerce_enum_to_str(cls, v: Any) -> str:
        """Convert WidgetType enum instance to its string value."""
        return v.value if hasattr(v, "value") else str(v)


class DashboardWithWidgetsResponse(DashboardResponse):
    """Dashboard response with nested widgets list."""
    widgets: list[WidgetResponse] = Field(default_factory=list)
