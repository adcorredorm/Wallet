"""
Category service containing business logic for category operations.

Every public method accepts a user_id parameter and passes it to the
repository so queries are always scoped to a single user.
"""

from datetime import datetime
from uuid import UUID

from app.models import Category
from app.repositories import CategoryRepository
from app.utils.exceptions import NotFoundError, BusinessRuleError


class CategoryService:
    """Service for category business logic."""

    def __init__(self):
        """Initialize category service with repository."""
        self.repository = CategoryRepository()

    def get_all(
        self,
        user_id: UUID,
        type: str | None = None,
        include_archived: bool = False,
        updated_since: datetime | None = None,
    ) -> list[Category]:
        """
        Get all categories for a user, optionally filtered by type, archived
        status, and update time.

        Args:
            user_id: Owner's UUID.
            type: Optional category type filter (income, expense, both).
                Mutually exclusive with updated_since — raises ValueError if both
                are provided, because get_by_type() does not support time-based
                filtering. Sync callers must not pass type.
            include_archived: When True, return both active and archived categories.
                When False (default), return only active categories.
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all matching records.

        Returns:
            List of categories.

        Raises:
            ValueError: If both type and updated_since are provided.
        """
        if type and updated_since is not None:
            raise ValueError(
                "type and updated_since are mutually exclusive: get_by_type() "
                "does not support time-based filtering. Sync callers must not pass type."
            )
        if type:
            from app.models.category import CategoryType

            return self.repository.get_by_type(CategoryType(type), user_id=user_id)
        return self.repository.get_all(
            user_id=user_id,
            include_archived=include_archived,
            updated_since=updated_since,
        )

    def get_by_id(self, category_id: UUID, user_id: UUID) -> Category:
        """
        Get a category by ID, scoped to the owner.

        Args:
            category_id: Category UUID.
            user_id: Owner's UUID.

        Returns:
            Category instance.

        Raises:
            NotFoundError: If category not found or not owned by this user.
        """
        return self.repository.get_by_id_or_fail(category_id, user_id)

    def get_with_subcategories(
        self, category_id: UUID, user_id: UUID
    ) -> Category:
        """
        Get a category with its subcategories.

        Args:
            category_id: Category UUID.
            user_id: Owner's UUID.

        Returns:
            Category instance with subcategories loaded.

        Raises:
            NotFoundError: If category not found or not owned by this user.
        """
        category = self.repository.get_with_subcategories(category_id, user_id)
        if not category:
            raise NotFoundError("Category", str(category_id))
        return category

    def get_parent_categories(self, user_id: UUID) -> list[Category]:
        """
        Get all parent categories (categories without a parent) for a user.

        Args:
            user_id: Owner's UUID.

        Returns:
            List of parent categories.
        """
        return self.repository.get_parent_categories(user_id=user_id)

    def create(
        self,
        user_id: UUID,
        name: str,
        type: str,
        icon: str | None = None,
        color: str | None = None,
        parent_category_id: UUID | None = None,
        offline_id: str | None = None,
    ) -> Category:
        """
        Create a new category for a user.

        If offline_id is provided and a record with that key already exists in
        the database the existing category is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        Args:
            user_id: Owner's UUID.
            name: Category name.
            type: Category type (income, expense, both).
            icon: Optional icon identifier.
            color: Optional color in hex format.
            parent_category_id: Optional parent category ID.
            offline_id: Optional client-generated idempotency key.

        Returns:
            Created or pre-existing category instance.

        Raises:
            NotFoundError: If parent category not found.
            BusinessRuleError: If parent category type is incompatible.
        """
        from app.models.category import CategoryType

        if offline_id:
            existing = self.repository.get_by_offline_id(offline_id, user_id)
            if existing:
                return existing

        if parent_category_id:
            parent = self.repository.get_by_id_or_fail(parent_category_id, user_id)

            type_enum = CategoryType(type)
            if parent.type != CategoryType.BOTH and parent.type != type_enum:
                if type_enum != CategoryType.BOTH:
                    raise BusinessRuleError(
                        f"La subcategoria debe ser del mismo tipo que la categoria padre "
                        f"o tipo AMBOS. Padre: {parent.type.value}, hijo: {type}"
                    )

        return self.repository.create(
            user_id=user_id,
            name=name,
            type=CategoryType(type),
            icon=icon,
            color=color,
            parent_category_id=parent_category_id,
            offline_id=offline_id,
        )

    def update(
        self,
        category_id: UUID,
        user_id: UUID,
        name: str | None = None,
        type: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        parent_category_id: UUID | None = None,
        active: bool | None = None,
    ) -> Category:
        """
        Update an existing category.

        Args:
            category_id: Category UUID.
            user_id: Owner's UUID.
            name: New category name.
            type: New category type.
            icon: New icon identifier.
            color: New color.
            parent_category_id: New parent category ID.
            active: When provided, sets the active/archived flag directly.

        Returns:
            Updated category instance.

        Raises:
            NotFoundError: If category or parent not found.
            BusinessRuleError: If update would create circular reference.
        """
        from app.models.category import CategoryType

        category = self.repository.get_by_id_or_fail(category_id, user_id)

        if parent_category_id and parent_category_id == category_id:
            raise BusinessRuleError("Una categoria no puede ser su propio padre")

        if parent_category_id:
            parent = self.repository.get_by_id_or_fail(parent_category_id, user_id)

            if parent.parent_category_id == category_id:
                raise BusinessRuleError(
                    "No se puede crear una referencia circular entre categorias"
                )

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if type is not None:
            update_data["type"] = CategoryType(type)
        if icon is not None:
            update_data["icon"] = icon
        if color is not None:
            update_data["color"] = color
        if parent_category_id is not None:
            update_data["parent_category_id"] = parent_category_id
        if active is not None:
            update_data["active"] = active

        return self.repository.update(category, **update_data)

    def archive(self, category_id: UUID, user_id: UUID) -> None:
        """
        Archive a category by setting active=False.

        Does not check for subcategories or transactions — archiving is
        non-destructive and can always be reversed.

        Args:
            category_id: Category UUID.
            user_id: Owner's UUID.

        Raises:
            NotFoundError: If category not found or not owned by this user.
        """
        category = self.repository.get_by_id_or_fail(category_id, user_id)
        self.repository.update(category, active=False)

    def hard_delete(self, category_id: UUID, user_id: UUID) -> None:
        """
        Permanently delete a category from the database.

        Args:
            category_id: Category UUID.
            user_id: Owner's UUID.

        Raises:
            NotFoundError: If category not found or not owned by this user.
            BusinessRuleError: If category has transactions or subcategories.
        """
        category = self.repository.get_by_id_or_fail(category_id, user_id)

        if category.subcategories.count() > 0:
            raise BusinessRuleError(
                "No se puede eliminar una categoria con subcategorias"
            )

        if self.repository.has_transactions(category_id):
            raise BusinessRuleError(
                "No se puede eliminar una categoria con transacciones"
            )

        self.repository.delete(category)

    def delete(self, category_id: UUID, user_id: UUID) -> None:
        """
        Delete a category.

        Delegates to hard_delete for backward compatibility.

        Args:
            category_id: Category UUID.
            user_id: Owner's UUID.

        Raises:
            NotFoundError: If category not found or not owned by this user.
            BusinessRuleError: If category has transactions or subcategories.
        """
        self.hard_delete(category_id, user_id)
