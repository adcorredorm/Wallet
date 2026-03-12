"""
Pydantic schemas for UserSetting request validation and response serialisation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SettingUpdateRequest(BaseModel):
    """
    Schema for updating a single setting.

    The ``value`` field accepts any JSON-compatible Python type. Per-key
    business-rule validation is performed in the service layer rather than
    here, because the valid type and range depend on which key is being set.

    Attributes:
        value: New setting value (string, number, boolean, list, or dict).
    """

    value: Any


class SettingResponse(BaseModel):
    """
    Schema for a single setting in API responses.

    Attributes:
        key: Setting identifier (e.g. ``'primary_currency'``).
        value: Current stored value.
        updated_at: Timestamp of the last write for this row.
    """

    key: str
    value: Any
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingsResponse(BaseModel):
    """
    Schema for the get-all-settings endpoint response.

    Attributes:
        settings: Flat dictionary mapping every stored key to its value.
    """

    settings: dict[str, Any]
