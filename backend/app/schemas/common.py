"""
Common Pydantic schemas used across the application.
"""

from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response schema.

    Args:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_pages: Total number of pages
    """

    items: list[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
