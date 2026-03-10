"""
Unit tests for TransactionService.

These tests focus on business logic validation using mocked repositories.
No database, no Flask app context, no db.session — pure unit tests.
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4
from unittest.mock import Mock, patch

from app.services.transaction import TransactionService
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category, CategoryType
from app.models.account import Account
from app.utils.exceptions import NotFoundError, BusinessRuleError


# ============================================================================
# LOCAL FIXTURES
# ============================================================================

@pytest.fixture
def mock_transaction_repo():
    """Create a mocked TransactionRepository patched at the service module level."""
    with patch('app.services.transaction.TransactionRepository') as mock:
        yield mock.return_value


@pytest.fixture
def mock_account_repo():
    """Create a mocked AccountRepository patched at the service module level."""
    with patch('app.services.transaction.AccountRepository') as mock:
        yield mock.return_value


@pytest.fixture
def mock_category_repo():
    """Create a mocked CategoryRepository patched at the service module level."""
    with patch('app.services.transaction.CategoryRepository') as mock:
        yield mock.return_value


@pytest.fixture
def transaction_service(mock_transaction_repo, mock_account_repo, mock_category_repo):
    """
    Create a TransactionService instance with all repository dependencies mocked.

    All three patch fixtures must be active before TransactionService() is
    called so that __init__ receives mocked classes. Repository attributes are
    then overwritten with mock instances for deterministic access.
    """
    service = TransactionService()
    service.repository = mock_transaction_repo
    service.account_repository = mock_account_repo
    service.category_repository = mock_category_repo
    return service


@pytest.fixture
def sample_transaction():
    """
    Create a sample Transaction mock for testing.

    tipo and categoria_id are set so that the update path can read the
    effective values when only one of them is changing.
    """
    transaction = Mock(spec=Transaction)
    transaction.id = uuid4()
    transaction.tipo = TransactionType.GASTO
    transaction.monto = Decimal("250.00")
    transaction.fecha = date(2026, 3, 1)
    transaction.cuenta_id = uuid4()
    transaction.categoria_id = uuid4()
    transaction.titulo = "Compra supermercado"
    transaction.descripcion = "Descripción test"
    transaction.tags = ["test"]
    transaction.client_id = None
    return transaction


# ============================================================================
# HELPERS
# ============================================================================

def _make_account() -> Mock:
    """Return a bare Mock with Account spec."""
    return Mock(spec=Account)


def _make_category(tipo: CategoryType) -> Mock:
    """Return a Mock with Category spec and the given tipo set."""
    cat = Mock(spec=Category)
    cat.tipo = tipo
    return cat


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestGetById:
    """Tests for TransactionService.get_by_id."""

    def test_get_by_id_success(
        self, transaction_service, mock_transaction_repo, sample_transaction
    ):
        """Should return the transaction when the repository finds it."""
        mock_transaction_repo.get_with_relations.return_value = sample_transaction

        result = transaction_service.get_by_id(sample_transaction.id)

        mock_transaction_repo.get_with_relations.assert_called_once_with(
            sample_transaction.id
        )
        assert result == sample_transaction

    def test_get_by_id_not_found(
        self, transaction_service, mock_transaction_repo
    ):
        """Should raise NotFoundError when the repository returns None."""
        mock_transaction_repo.get_with_relations.return_value = None

        with pytest.raises(NotFoundError):
            transaction_service.get_by_id(uuid4())


class TestGetFiltered:
    """Tests for TransactionService.get_filtered."""

    def test_get_filtered_pagination_offset_calculated(
        self, transaction_service, mock_transaction_repo, sample_transaction
    ):
        """Should compute offset = (page - 1) * limit before querying."""
        mock_transaction_repo.get_filtered.return_value = ([sample_transaction], 1)

        result, total = transaction_service.get_filtered(page=2, limit=10)

        call_kwargs = mock_transaction_repo.get_filtered.call_args.kwargs
        assert call_kwargs["offset"] == 10  # (2-1) * 10
        assert call_kwargs["limit"] == 10
        assert total == 1

    def test_get_filtered_with_tipo_converts_to_enum(
        self, transaction_service, mock_transaction_repo, sample_transaction
    ):
        """Should convert tipo string to TransactionType enum before querying."""
        mock_transaction_repo.get_filtered.return_value = ([sample_transaction], 1)

        transaction_service.get_filtered(tipo="gasto")

        call_kwargs = mock_transaction_repo.get_filtered.call_args.kwargs
        assert call_kwargs["tipo"] == TransactionType.GASTO


class TestCreate:
    """Tests for TransactionService.create."""

    def test_create_valid_transaction(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """Should create transaction when account and category exist with compatible types."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.GASTO
        )
        mock_transaction_repo.create.return_value = sample_transaction

        result = transaction_service.create(
            tipo="gasto",
            monto=Decimal("100.00"),
            fecha=date(2026, 3, 1),
            cuenta_id=uuid4(),
            categoria_id=uuid4(),
        )

        assert result == sample_transaction
        mock_transaction_repo.create.assert_called_once()

    def test_create_ingreso_with_ambos_category_is_valid(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """INGRESO transaction with AMBOS category should succeed."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.AMBOS
        )
        mock_transaction_repo.create.return_value = sample_transaction

        result = transaction_service.create(
            tipo="ingreso",
            monto=Decimal("500.00"),
            fecha=date(2026, 3, 1),
            cuenta_id=uuid4(),
            categoria_id=uuid4(),
        )

        assert result == sample_transaction

    def test_create_idempotency_returns_existing_record(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """Should return the existing transaction immediately when client_id matches."""
        mock_transaction_repo.get_by_client_id.return_value = sample_transaction

        result = transaction_service.create(
            tipo="gasto",
            monto=Decimal("100.00"),
            fecha=date(2026, 3, 1),
            cuenta_id=uuid4(),
            categoria_id=uuid4(),
            client_id="client-key-abc",
        )

        assert result == sample_transaction
        # Must short-circuit: no account or category lookups, no creation
        mock_account_repo.get_by_id_or_fail.assert_not_called()
        mock_transaction_repo.create.assert_not_called()

    def test_create_account_not_found(
        self, transaction_service, mock_account_repo
    ):
        """Should raise NotFoundError when the account does not exist."""
        mock_account_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Account", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transaction_service.create(
                tipo="gasto",
                monto=Decimal("100.00"),
                fecha=date(2026, 3, 1),
                cuenta_id=uuid4(),
                categoria_id=uuid4(),
            )

    def test_create_category_not_found(
        self, transaction_service, mock_account_repo, mock_category_repo
    ):
        """Should raise NotFoundError when the category does not exist."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Category", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transaction_service.create(
                tipo="gasto",
                monto=Decimal("100.00"),
                fecha=date(2026, 3, 1),
                cuenta_id=uuid4(),
                categoria_id=uuid4(),
            )

    def test_create_gasto_with_ingreso_category_raises_business_rule_error(
        self,
        transaction_service,
        mock_account_repo,
        mock_category_repo,
    ):
        """Should raise BusinessRuleError when a GASTO transaction uses an INGRESO category."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.INGRESO
        )

        with pytest.raises(BusinessRuleError):
            transaction_service.create(
                tipo="gasto",
                monto=Decimal("100.00"),
                fecha=date(2026, 3, 1),
                cuenta_id=uuid4(),
                categoria_id=uuid4(),
            )

    def test_create_ingreso_with_gasto_category_raises_business_rule_error(
        self,
        transaction_service,
        mock_account_repo,
        mock_category_repo,
    ):
        """Should raise BusinessRuleError when an INGRESO transaction uses a GASTO category."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.GASTO
        )

        with pytest.raises(BusinessRuleError):
            transaction_service.create(
                tipo="ingreso",
                monto=Decimal("500.00"),
                fecha=date(2026, 3, 1),
                cuenta_id=uuid4(),
                categoria_id=uuid4(),
            )


class TestValidateCategoryType:
    """
    Tests for TransactionService._validate_category_type.

    Exercises all six transaction-type × category-type combinations documented
    in the plan to lock in the compatibility matrix.
    """

    def test_ingreso_transaction_with_ingreso_category_is_valid(
        self, transaction_service
    ):
        """INGRESO + INGRESO should not raise."""
        transaction_service._validate_category_type(
            TransactionType.INGRESO, CategoryType.INGRESO
        )

    def test_ingreso_transaction_with_ambos_category_is_valid(
        self, transaction_service
    ):
        """INGRESO + AMBOS should not raise."""
        transaction_service._validate_category_type(
            TransactionType.INGRESO, CategoryType.AMBOS
        )

    def test_gasto_transaction_with_gasto_category_is_valid(
        self, transaction_service
    ):
        """GASTO + GASTO should not raise."""
        transaction_service._validate_category_type(
            TransactionType.GASTO, CategoryType.GASTO
        )

    def test_gasto_transaction_with_ambos_category_is_valid(
        self, transaction_service
    ):
        """GASTO + AMBOS should not raise."""
        transaction_service._validate_category_type(
            TransactionType.GASTO, CategoryType.AMBOS
        )

    def test_ingreso_transaction_with_gasto_category_raises(
        self, transaction_service
    ):
        """INGRESO + GASTO should raise BusinessRuleError."""
        with pytest.raises(BusinessRuleError):
            transaction_service._validate_category_type(
                TransactionType.INGRESO, CategoryType.GASTO
            )

    def test_gasto_transaction_with_ingreso_category_raises(
        self, transaction_service
    ):
        """GASTO + INGRESO should raise BusinessRuleError."""
        with pytest.raises(BusinessRuleError):
            transaction_service._validate_category_type(
                TransactionType.GASTO, CategoryType.INGRESO
            )


class TestUpdate:
    """Tests for TransactionService.update."""

    def test_update_partial_fields(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """Should include only the provided fields in the repository update call."""
        mock_transaction_repo.get_by_id_or_fail.return_value = sample_transaction
        mock_transaction_repo.update.return_value = sample_transaction

        transaction_service.update(
            transaction_id=sample_transaction.id,
            monto=Decimal("999.00"),
        )

        call_kwargs = mock_transaction_repo.update.call_args[1]
        assert "monto" in call_kwargs
        assert "tipo" not in call_kwargs
        assert "fecha" not in call_kwargs

    def test_update_tipo_revalidates_category_compatibility(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """Should re-validate compatibility when transaction type changes."""
        # sample_transaction.tipo == GASTO, existing category will be fetched
        # by categoria_id from the transaction mock
        gasto_category = Mock(spec=Category)
        gasto_category.tipo = CategoryType.GASTO  # incompatible with new INGRESO tipo

        mock_transaction_repo.get_by_id_or_fail.return_value = sample_transaction
        mock_category_repo.get_by_id_or_fail.return_value = gasto_category

        with pytest.raises(BusinessRuleError):
            transaction_service.update(
                transaction_id=sample_transaction.id,
                tipo="ingreso",  # changing type but not category → re-validation fires
            )

    def test_update_categoria_revalidates_type_compatibility(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """Should re-validate compatibility when category changes."""
        ingreso_category = Mock(spec=Category)
        ingreso_category.tipo = CategoryType.INGRESO  # incompatible with existing GASTO tipo

        mock_transaction_repo.get_by_id_or_fail.return_value = sample_transaction
        mock_category_repo.get_by_id_or_fail.return_value = ingreso_category

        with pytest.raises(BusinessRuleError):
            transaction_service.update(
                transaction_id=sample_transaction.id,
                categoria_id=uuid4(),  # changing category → re-validation with existing GASTO tipo
            )

    def test_update_not_found(
        self, transaction_service, mock_transaction_repo
    ):
        """Should raise NotFoundError when the transaction does not exist."""
        mock_transaction_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Transaction", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transaction_service.update(
                transaction_id=uuid4(), monto=Decimal("100.00")
            )


class TestDelete:
    """Tests for TransactionService.delete."""

    def test_delete_success(
        self, transaction_service, mock_transaction_repo, sample_transaction
    ):
        """Should call repository.delete with the fetched transaction object."""
        mock_transaction_repo.get_by_id_or_fail.return_value = sample_transaction

        transaction_service.delete(sample_transaction.id)

        mock_transaction_repo.delete.assert_called_once_with(sample_transaction)

    def test_delete_not_found(
        self, transaction_service, mock_transaction_repo
    ):
        """Should raise NotFoundError and never call delete when transaction is absent."""
        mock_transaction_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Transaction", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transaction_service.delete(uuid4())

        mock_transaction_repo.delete.assert_not_called()
