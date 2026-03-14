"""
Category repository for database operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.extensions import db
from app.models import Category, CategoryType
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category entity operations."""

    def __init__(self):
        """Initialize category repository."""
        super().__init__(Category)

    def get_by_type(self, type: CategoryType) -> list[Category]:
        """
        Get all categories of a specific type.

        Args:
            type: Category type (INCOME, EXPENSE, BOTH)

        Returns:
            List of categories matching the type
        """
        return (
            db.session.execute(db.select(Category).where(Category.type == type))
            .scalars()
            .all()
        )

    def get_parent_categories(self) -> list[Category]:
        """
        Get all parent categories (categories without a parent).

        Returns:
            List of parent categories
        """
        return (
            db.session.execute(
                db.select(Category).where(Category.parent_category_id == None)
            )
            .scalars()
            .all()
        )

    def get_subcategories(self, parent_id: UUID) -> list[Category]:
        """
        Get all subcategories of a parent category.

        Args:
            parent_id: Parent category UUID

        Returns:
            List of subcategories
        """
        return (
            db.session.execute(
                db.select(Category).where(Category.parent_category_id == parent_id)
            )
            .scalars()
            .all()
        )

    def get_with_subcategories(self, category_id: UUID) -> Optional[Category]:
        """
        Get a category with its subcategories eagerly loaded.

        Args:
            category_id: Category UUID

        Returns:
            Category instance with subcategories or None
        """
        from sqlalchemy.orm import selectinload

        return db.session.execute(
            db.select(Category)
            .where(Category.id == category_id)
            .options(selectinload(Category.subcategories))
        ).scalar_one_or_none()

    def get_all_active(self) -> list[Category]:
        """
        Get all active (non-archived) categories.

        Returns:
            List of categories where active is True
        """
        return (
            db.session.execute(db.select(Category).where(Category.active == True))
            .scalars()
            .all()
        )

    def get_all(
        self,
        include_archived: bool = False,
        updated_since: datetime | None = None,
    ) -> list[Category]:
        """
        Get all categories, optionally filtered by archived status and/or update time.

        Args:
            include_archived: When True, return all categories regardless of
                active flag. When False (default), return only active categories.
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all matching records.

        Returns:
            List of categories
        """
        query = db.select(Category)
        if not include_archived:
            query = query.where(Category.active == True)
        if updated_since is not None:
            query = query.where(Category.updated_at >= updated_since)
        return db.session.execute(query).scalars().all()

    def has_transactions(self, category_id: UUID) -> bool:
        """
        Check if a category has associated transactions.

        Args:
            category_id: Category UUID

        Returns:
            True if category has transactions, False otherwise
        """
        from app.models import Transaction

        count = (
            db.session.query(Transaction)
            .filter(Transaction.category_id == category_id)
            .count()
        )
        return count > 0
