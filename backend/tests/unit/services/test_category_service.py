"""
Unit tests for CategoryService.

These tests focus on business logic validation using mocked repositories.
No database, no Flask app context, no db.session — pure unit tests.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch

from app.services.category import CategoryService
from app.models.category import Category, CategoryType
from app.utils.exceptions import NotFoundError, BusinessRuleError


# ============================================================================
# LOCAL FIXTURES
# ============================================================================

@pytest.fixture
def mock_repository():
    """Create a mocked CategoryRepository patched at the service module level."""
    with patch('app.services.category.CategoryRepository') as mock:
        yield mock.return_value


@pytest.fixture
def category_service(mock_repository):
    """Create CategoryService instance with mocked repository."""
    service = CategoryService()
    service.repository = mock_repository
    return service


@pytest.fixture
def sample_category():
    """
    Create a sample Category mock for testing.

    Includes dynamic relationship mocks (.subcategorias, .transacciones)
    with count() returning 0 by default so delete guards pass unless overridden.
    """
    category = Mock(spec=Category)
    category.id = uuid4()
    category.nombre = "Alimentación"
    category.tipo = CategoryType.GASTO
    category.icono = "food-icon"
    category.color = "#FF5733"
    category.categoria_padre_id = None

    category.subcategorias = Mock()
    category.subcategorias.count.return_value = 0
    category.transacciones = Mock()
    category.transacciones.count.return_value = 0

    return category


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestGetAll:
    """Tests for CategoryService.get_all."""

    def test_get_all_without_filter_returns_all(
        self, category_service, mock_repository, sample_category
    ):
        """Should call repository.get_all when no type filter is provided."""
        mock_repository.get_all.return_value = [sample_category]

        result = category_service.get_all()

        mock_repository.get_all.assert_called_once()
        mock_repository.get_by_type.assert_not_called()
        assert len(result) == 1

    def test_get_all_with_type_filter_calls_get_by_type(
        self, category_service, mock_repository, sample_category
    ):
        """Should call repository.get_by_type with the correct enum when tipo is provided."""
        mock_repository.get_by_type.return_value = [sample_category]

        result = category_service.get_all(tipo="gasto")

        mock_repository.get_by_type.assert_called_once_with(CategoryType.GASTO)
        mock_repository.get_all.assert_not_called()
        assert len(result) == 1

    def test_get_all_type_ingreso_filter(
        self, category_service, mock_repository, sample_category
    ):
        """Should pass CategoryType.INGRESO to get_by_type when tipo='ingreso'."""
        mock_repository.get_by_type.return_value = [sample_category]

        category_service.get_all(tipo="ingreso")

        mock_repository.get_by_type.assert_called_once_with(CategoryType.INGRESO)


class TestGetWithSubcategories:
    """Tests for CategoryService.get_with_subcategories."""

    def test_get_with_subcategories_success(
        self, category_service, mock_repository, sample_category
    ):
        """Should return the category when the repository finds it."""
        mock_repository.get_with_subcategories.return_value = sample_category

        result = category_service.get_with_subcategories(sample_category.id)

        mock_repository.get_with_subcategories.assert_called_once_with(sample_category.id)
        assert result == sample_category

    def test_get_with_subcategories_not_found(
        self, category_service, mock_repository
    ):
        """Should raise NotFoundError when the repository returns None."""
        category_id = uuid4()
        mock_repository.get_with_subcategories.return_value = None

        with pytest.raises(NotFoundError):
            category_service.get_with_subcategories(category_id)


class TestCreate:
    """Tests for CategoryService.create."""

    def test_create_valid_category_without_parent(
        self, category_service, mock_repository, sample_category
    ):
        """Should create a root category (no parent) without any compatibility check."""
        mock_repository.create.return_value = sample_category

        result = category_service.create(nombre="Transporte", tipo="gasto")

        assert result == sample_category
        mock_repository.create.assert_called_once()
        # No parent validation should be attempted
        mock_repository.get_by_id_or_fail.assert_not_called()

    def test_create_valid_subcategory_with_matching_parent_type(
        self, category_service, mock_repository, sample_category
    ):
        """Should create subcategory when parent type equals child type."""
        parent = Mock(spec=Category)
        parent.id = uuid4()
        parent.tipo = CategoryType.GASTO

        mock_repository.get_by_id_or_fail.return_value = parent
        mock_repository.create.return_value = sample_category

        result = category_service.create(
            nombre="Restaurantes",
            tipo="gasto",
            categoria_padre_id=parent.id,
        )

        assert result == sample_category
        mock_repository.create.assert_called_once()

    def test_create_subcategory_incompatible_type_raises_business_rule_error(
        self, category_service, mock_repository
    ):
        """Should raise BusinessRuleError when child type conflicts with parent type."""
        parent = Mock(spec=Category)
        parent.id = uuid4()
        parent.tipo = CategoryType.INGRESO  # INGRESO parent

        mock_repository.get_by_id_or_fail.return_value = parent

        with pytest.raises(BusinessRuleError):
            category_service.create(
                nombre="Comida",
                tipo="gasto",  # GASTO child under INGRESO parent → invalid
                categoria_padre_id=parent.id,
            )

    def test_create_subcategory_ambos_parent_allows_any_child_type(
        self, category_service, mock_repository, sample_category
    ):
        """Should allow any child type when parent type is AMBOS."""
        parent = Mock(spec=Category)
        parent.id = uuid4()
        parent.tipo = CategoryType.AMBOS

        mock_repository.get_by_id_or_fail.return_value = parent
        mock_repository.create.return_value = sample_category

        result = category_service.create(
            nombre="Subcategoría mixta",
            tipo="gasto",
            categoria_padre_id=parent.id,
        )

        assert result == sample_category

    def test_create_subcategory_ambos_child_under_typed_parent_is_allowed(
        self, category_service, mock_repository, sample_category
    ):
        """AMBOS child under a typed parent should be allowed (inner guard: if tipo_enum != AMBOS)."""
        parent = Mock(spec=Category)
        parent.id = uuid4()
        parent.tipo = CategoryType.INGRESO  # typed parent

        mock_repository.get_by_id_or_fail.return_value = parent
        mock_repository.create.return_value = sample_category

        # AMBOS child under INGRESO parent: outer condition triggers but inner guard lets it pass
        result = category_service.create(
            nombre="Categoría mixta",
            tipo="ambos",
            categoria_padre_id=parent.id,
        )

        assert result == sample_category
        mock_repository.create.assert_called_once()

    def test_create_idempotency_returns_existing_record(
        self, category_service, mock_repository, sample_category
    ):
        """Should return the existing category without re-creating when client_id matches."""
        mock_repository.get_by_client_id.return_value = sample_category

        result = category_service.create(
            nombre="Duplicate",
            tipo="gasto",
            client_id="client-key-xyz",
        )

        assert result == sample_category
        mock_repository.create.assert_not_called()


class TestUpdate:
    """Tests for CategoryService.update."""

    def test_update_partial_fields(
        self, category_service, mock_repository, sample_category
    ):
        """Should include only the provided fields in the repository update call."""
        updated = Mock(spec=Category)
        mock_repository.get_by_id_or_fail.return_value = sample_category
        mock_repository.update.return_value = updated

        category_service.update(
            category_id=sample_category.id,
            nombre="Nuevo nombre",
        )

        call_kwargs = mock_repository.update.call_args[1]
        assert "nombre" in call_kwargs
        assert "tipo" not in call_kwargs
        assert "color" not in call_kwargs

    def test_update_success_returns_updated_category(
        self, category_service, mock_repository, sample_category
    ):
        """Should return the updated category from the repository."""
        updated = Mock(spec=Category)
        mock_repository.get_by_id_or_fail.return_value = sample_category
        mock_repository.update.return_value = updated

        result = category_service.update(
            category_id=sample_category.id,
            nombre="Nombre actualizado",
            color="#00FF00",
        )

        assert result == updated

    def test_update_self_as_parent_raises_business_rule_error(
        self, category_service, mock_repository, sample_category
    ):
        """Should raise BusinessRuleError when a category is set as its own parent."""
        mock_repository.get_by_id_or_fail.return_value = sample_category

        with pytest.raises(BusinessRuleError) as exc_info:
            category_service.update(
                category_id=sample_category.id,
                categoria_padre_id=sample_category.id,  # self-reference
            )

        assert "padre" in str(exc_info.value).lower()

    def test_update_circular_reference_raises_business_rule_error(
        self, category_service, mock_repository, sample_category
    ):
        """Should raise BusinessRuleError when setting parent would create a circular reference."""
        parent = Mock(spec=Category)
        parent.id = uuid4()
        # The proposed parent already has sample_category as its own parent
        parent.categoria_padre_id = sample_category.id

        mock_repository.get_by_id_or_fail.side_effect = [sample_category, parent]

        with pytest.raises(BusinessRuleError) as exc_info:
            category_service.update(
                category_id=sample_category.id,
                categoria_padre_id=parent.id,
            )

        assert "circular" in str(exc_info.value).lower()

    def test_update_not_found(self, category_service, mock_repository):
        """Should raise NotFoundError when the category does not exist."""
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError(
            "Category", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            category_service.update(category_id=uuid4(), nombre="Test")


class TestDelete:
    """Tests for CategoryService.delete."""

    def test_delete_success(
        self, category_service, mock_repository, sample_category
    ):
        """Should delete when the category has no subcategories and no transactions."""
        mock_repository.get_by_id_or_fail.return_value = sample_category
        mock_repository.has_transactions.return_value = False

        category_service.delete(sample_category.id)

        mock_repository.delete.assert_called_once_with(sample_category)

    def test_delete_with_subcategories_raises_business_rule_error(
        self, category_service, mock_repository, sample_category
    ):
        """Should raise BusinessRuleError when the category has subcategories."""
        sample_category.subcategorias.count.return_value = 2
        mock_repository.get_by_id_or_fail.return_value = sample_category

        with pytest.raises(BusinessRuleError) as exc_info:
            category_service.delete(sample_category.id)

        assert "subcategoria" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_with_transactions_raises_business_rule_error(
        self, category_service, mock_repository, sample_category
    ):
        """Should raise BusinessRuleError when the category has associated transactions."""
        mock_repository.get_by_id_or_fail.return_value = sample_category
        mock_repository.has_transactions.return_value = True

        with pytest.raises(BusinessRuleError) as exc_info:
            category_service.delete(sample_category.id)

        assert "transaccion" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_not_found(self, category_service, mock_repository):
        """Should raise NotFoundError when the category does not exist."""
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError(
            "Category", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            category_service.delete(uuid4())

        mock_repository.delete.assert_not_called()
