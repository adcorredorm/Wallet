"""
Category model for organizing transactions.

Categories can be for income, expenses, or both. They support hierarchical
organization through parent-child relationships.
"""

import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, String, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class CategoryType(enum.Enum):
    """Enumeration of category types."""

    INCOME = "income"
    EXPENSE = "expense"
    BOTH = "both"


class Category(BaseModel):
    """
    Category model for transaction classification.

    Attributes:
        name: Category name (max 50 characters)
        type: Category type (income, expense, or both)
        icon: Optional icon identifier
        color: Optional color in hex format (#RRGGBB)
        parent_category_id: Optional parent category ID for subcategories
        active: Whether the category is active (False = archived/soft-deleted)
        parent_category: Parent category relationship
        subcategories: Child categories relationship
        transactions: Related transactions
    """

    __tablename__ = "categories"

    name = Column(String(50), nullable=False)
    type = Column(Enum(CategoryType), nullable=False)
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)  # #RRGGBB
    parent_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True,
    )
    active = Column(Boolean, nullable=False, default=True)

    # Relationships
    parent_category = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="subcategories",
    )
    subcategories = relationship(
        "Category",
        back_populates="parent_category",
        lazy="dynamic",
    )
    transactions = relationship(
        "Transaction",
        back_populates="category",
        lazy="dynamic",
    )

    # Indexes
    __table_args__ = (
        Index("idx_categories_type", "type"),
        Index("idx_categories_parent", "parent_category_id"),
        Index("idx_categories_active", "active"),
    )

    def __repr__(self) -> str:
        """String representation of the category."""
        return f"<Category {self.name} ({self.type.value})>"
