"""
Category service containing business logic for category operations.
"""

from uuid import UUID

from app.models import Category
from app.repositories import CategoryRepository
from app.utils.exceptions import NotFoundError, BusinessRuleError


class CategoryService:
    """Service for category business logic."""

    def __init__(self):
        """Initialize category service with repository."""
        self.repository = CategoryRepository()

    def get_all(self, tipo: str | None = None) -> list[Category]:
        """
        Get all categories, optionally filtered by type.

        Args:
            tipo: Optional category type filter (ingreso, gasto, ambos)

        Returns:
            List of categories
        """
        if tipo:
            from app.models.category import CategoryType

            return self.repository.get_by_type(CategoryType(tipo))
        return self.repository.get_all()

    def get_by_id(self, category_id: UUID) -> Category:
        """
        Get a category by ID.

        Args:
            category_id: Category UUID

        Returns:
            Category instance

        Raises:
            NotFoundError: If category not found
        """
        return self.repository.get_by_id_or_fail(category_id)

    def get_with_subcategories(self, category_id: UUID) -> Category:
        """
        Get a category with its subcategories.

        Args:
            category_id: Category UUID

        Returns:
            Category instance with subcategories loaded

        Raises:
            NotFoundError: If category not found
        """
        category = self.repository.get_with_subcategories(category_id)
        if not category:
            raise NotFoundError("Category", str(category_id))
        return category

    def get_parent_categories(self) -> list[Category]:
        """
        Get all parent categories (categories without a parent).

        Returns:
            List of parent categories
        """
        return self.repository.get_parent_categories()

    def create(
        self,
        nombre: str,
        tipo: str,
        icono: str | None = None,
        color: str | None = None,
        categoria_padre_id: UUID | None = None,
    ) -> Category:
        """
        Create a new category.

        Args:
            nombre: Category name
            tipo: Category type (ingreso, gasto, ambos)
            icono: Optional icon identifier
            color: Optional color in hex format
            categoria_padre_id: Optional parent category ID

        Returns:
            Created category instance

        Raises:
            NotFoundError: If parent category not found
            BusinessRuleError: If parent category type is incompatible
        """
        from app.models.category import CategoryType

        # Validate parent category if provided
        if categoria_padre_id:
            parent = self.repository.get_by_id_or_fail(categoria_padre_id)

            # Validate type compatibility
            tipo_enum = CategoryType(tipo)
            if parent.tipo != CategoryType.AMBOS and parent.tipo != tipo_enum:
                if tipo_enum != CategoryType.AMBOS:
                    raise BusinessRuleError(
                        f"La subcategoria debe ser del mismo tipo que la categoria padre "
                        f"o tipo AMBOS. Padre: {parent.tipo.value}, hijo: {tipo}"
                    )

        return self.repository.create(
            nombre=nombre,
            tipo=CategoryType(tipo),
            icono=icono,
            color=color,
            categoria_padre_id=categoria_padre_id,
        )

    def update(
        self,
        category_id: UUID,
        nombre: str | None = None,
        tipo: str | None = None,
        icono: str | None = None,
        color: str | None = None,
        categoria_padre_id: UUID | None = None,
    ) -> Category:
        """
        Update an existing category.

        Args:
            category_id: Category UUID
            nombre: New category name
            tipo: New category type
            icono: New icon identifier
            color: New color
            categoria_padre_id: New parent category ID

        Returns:
            Updated category instance

        Raises:
            NotFoundError: If category or parent not found
            BusinessRuleError: If update would create circular reference
        """
        from app.models.category import CategoryType

        category = self.repository.get_by_id_or_fail(category_id)

        # Prevent setting self as parent
        if categoria_padre_id and categoria_padre_id == category_id:
            raise BusinessRuleError("Una categoria no puede ser su propio padre")

        # Validate parent category if changing
        if categoria_padre_id:
            parent = self.repository.get_by_id_or_fail(categoria_padre_id)

            # Prevent circular references (parent can't be a child of this category)
            if parent.categoria_padre_id == category_id:
                raise BusinessRuleError(
                    "No se puede crear una referencia circular entre categorias"
                )

        update_data = {}
        if nombre is not None:
            update_data["nombre"] = nombre
        if tipo is not None:
            update_data["tipo"] = CategoryType(tipo)
        if icono is not None:
            update_data["icono"] = icono
        if color is not None:
            update_data["color"] = color
        if categoria_padre_id is not None:
            update_data["categoria_padre_id"] = categoria_padre_id

        return self.repository.update(category, **update_data)

    def delete(self, category_id: UUID) -> None:
        """
        Delete a category.

        Args:
            category_id: Category UUID

        Raises:
            NotFoundError: If category not found
            BusinessRuleError: If category has transactions or subcategories
        """
        category = self.repository.get_by_id_or_fail(category_id)

        # Check if category has subcategories
        if category.subcategorias.count() > 0:
            raise BusinessRuleError(
                "No se puede eliminar una categoria con subcategorias"
            )

        # Check if category has transactions
        if self.repository.has_transactions(category_id):
            raise BusinessRuleError(
                "No se puede eliminar una categoria con transacciones"
            )

        self.repository.delete(category)
