"""
Category repository for database operations.
"""

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

    def get_by_type(self, tipo: CategoryType) -> list[Category]:
        """
        Get all categories of a specific type.

        Args:
            tipo: Category type (INGRESO, GASTO, AMBOS)

        Returns:
            List of categories matching the type
        """
        return (
            db.session.execute(db.select(Category).where(Category.tipo == tipo))
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
                db.select(Category).where(Category.categoria_padre_id == None)
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
                db.select(Category).where(Category.categoria_padre_id == parent_id)
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
            .options(selectinload(Category.subcategorias))
        ).scalar_one_or_none()

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
            .filter(Transaction.categoria_id == category_id)
            .count()
        )
        return count > 0
