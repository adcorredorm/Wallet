"""
Category Pydantic schemas for validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum
import re


class CategoryType(str, Enum):
    """Category type enumeration."""

    INCOME = "income"
    EXPENSE = "expense"
    BOTH = "both"


class CategoryCreate(BaseModel):
    """
    Schema for creating a new category.

    Args:
        name: Category name (1-50 characters)
        type: Category type (income, expense, or both)
        icon: Optional icon identifier (max 50 characters)
        color: Optional color in hex format (#RRGGBB)
        parent_category_id: Optional parent category ID for subcategories
        offline_id: Optional client-generated UUID for offline idempotency.
            When provided, a retry of the same creation request will return
            the existing record instead of creating a duplicate.
    """

    name: str = Field(..., min_length=1, max_length=50)
    type: CategoryType
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    parent_category_id: Optional[UUID] = None
    offline_id: Optional[str] = Field(None, max_length=100)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is in hex format and normalize to uppercase."""
        if v is None:
            return v
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color debe ser formato hexadecimal (#RRGGBB)")
        return v.upper()


class CategoryUpdate(BaseModel):
    """
    Schema for updating an existing category.

    All fields are optional to support partial updates.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    type: Optional[CategoryType] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = None
    parent_category_id: Optional[UUID] = None
    active: Optional[bool] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is in hex format and normalize to uppercase."""
        if v is None:
            return v
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color debe ser formato hexadecimal (#RRGGBB)")
        return v.upper()


class CategoryResponse(BaseModel):
    """
    Schema for category responses.

    Returns:
        Complete category information including metadata
    """

    id: UUID
    name: str
    type: CategoryType
    icon: Optional[str]
    color: Optional[str]
    parent_category_id: Optional[UUID]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryWithSubcategories(CategoryResponse):
    """
    Schema for category with its subcategories.

    Extends CategoryResponse with nested subcategories list.
    """

    subcategories: list["CategoryResponse"] = Field(
        default_factory=list, description="Child categories"
    )
