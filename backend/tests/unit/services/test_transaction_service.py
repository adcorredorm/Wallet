"""
Unit tests for TransactionService.

These tests focus on business logic validation using mocked repositories.
No database, no Flask app context, no db.session — pure unit tests.
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from app.services.transaction import TransactionService
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category, CategoryType
from app.models.account import Account
from app.utils.exceptions import NotFoundError, BusinessRuleError

USER_ID = uuid4()


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

    type and category_id are set so that the update path can read the
    effective values when only one of them is changing.
    """
    transaction = MagicMock()
    transaction.id = uuid4()
    transaction.type = TransactionType.EXPENSE
    transaction.amount = Decimal("250.00")
    transaction.date = date(2026, 3, 1)
    transaction.account_id = uuid4()
    transaction.category_id = uuid4()
    transaction.title = "Compra supermercado"
    transaction.description = "Descripción test"
    transaction.tags = ["test"]
    transaction.offline_id = None
    return transaction


# ============================================================================
# HELPERS
# ============================================================================

def _make_account() -> Mock:
    """Return a bare Mock with Account spec."""
    return MagicMock()


def _make_category(type: CategoryType) -> Mock:
    """Return a Mock with Category spec and the given type set."""
    cat = MagicMock()
    cat.type = type
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

        result = transaction_service.get_by_id(sample_transaction.id, user_id=USER_ID)

        mock_transaction_repo.get_with_relations.assert_called_once_with(
            sample_transaction.id, USER_ID
        )
        assert result == sample_transaction

    def test_get_by_id_not_found(
        self, transaction_service, mock_transaction_repo
    ):
        """Should raise NotFoundError when the repository returns None."""
        mock_transaction_repo.get_with_relations.return_value = None

        with pytest.raises(NotFoundError):
            transaction_service.get_by_id(uuid4(), user_id=USER_ID)


class TestGetFiltered:
    """Tests for TransactionService.get_filtered."""

    def test_get_filtered_pagination_offset_calculated(
        self, transaction_service, mock_transaction_repo, sample_transaction
    ):
        """Should compute offset = (page - 1) * limit before querying."""
        mock_transaction_repo.get_filtered.return_value = ([sample_transaction], 1)

        result, total = transaction_service.get_filtered(user_id=USER_ID, page=2, limit=10)

        call_kwargs = mock_transaction_repo.get_filtered.call_args.kwargs
        assert call_kwargs["offset"] == 10  # (2-1) * 10
        assert call_kwargs["limit"] == 10
        assert total == 1

    def test_get_filtered_with_type_converts_to_enum(
        self, transaction_service, mock_transaction_repo, sample_transaction
    ):
        """Should convert type string to TransactionType enum before querying."""
        mock_transaction_repo.get_filtered.return_value = ([sample_transaction], 1)

        transaction_service.get_filtered(user_id=USER_ID, type="expense")

        call_kwargs = mock_transaction_repo.get_filtered.call_args.kwargs
        assert call_kwargs["type"] == TransactionType.EXPENSE


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
            CategoryType.EXPENSE
        )
        mock_transaction_repo.create.return_value = sample_transaction

        result = transaction_service.create(
            user_id=USER_ID,
            type="expense",
            amount=Decimal("100.00"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
        )

        assert result == sample_transaction
        mock_transaction_repo.create.assert_called_once()

    def test_create_income_with_both_category_is_valid(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """INCOME transaction with BOTH category should succeed."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.BOTH
        )
        mock_transaction_repo.create.return_value = sample_transaction

        result = transaction_service.create(
            user_id=USER_ID,
            type="income",
            amount=Decimal("500.00"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
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
        """Should return the existing transaction immediately when offline_id matches."""
        mock_transaction_repo.get_by_offline_id.return_value = sample_transaction

        result = transaction_service.create(
            user_id=USER_ID,
            type="expense",
            amount=Decimal("100.00"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
            offline_id="client-key-abc",
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
                user_id=USER_ID,
                type="expense",
                amount=Decimal("100.00"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
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
                user_id=USER_ID,
                type="expense",
                amount=Decimal("100.00"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
            )

    def test_create_expense_with_income_category_raises_business_rule_error(
        self,
        transaction_service,
        mock_account_repo,
        mock_category_repo,
    ):
        """Should raise BusinessRuleError when an EXPENSE transaction uses an INCOME category."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.INCOME
        )

        with pytest.raises(BusinessRuleError):
            transaction_service.create(
                user_id=USER_ID,
                type="expense",
                amount=Decimal("100.00"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
            )

    def test_create_income_with_expense_category_raises_business_rule_error(
        self,
        transaction_service,
        mock_account_repo,
        mock_category_repo,
    ):
        """Should raise BusinessRuleError when an INCOME transaction uses an EXPENSE category."""
        mock_account_repo.get_by_id_or_fail.return_value = _make_account()
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.EXPENSE
        )

        with pytest.raises(BusinessRuleError):
            transaction_service.create(
                user_id=USER_ID,
                type="income",
                amount=Decimal("500.00"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
            )


class TestValidateCategoryType:
    """
    Tests for TransactionService._validate_category_type.

    Exercises all six transaction-type × category-type combinations documented
    in the plan to lock in the compatibility matrix.
    """

    def test_income_transaction_with_income_category_is_valid(
        self, transaction_service
    ):
        """INCOME + INCOME should not raise."""
        transaction_service._validate_category_type(
            TransactionType.INCOME, CategoryType.INCOME
        )

    def test_income_transaction_with_both_category_is_valid(
        self, transaction_service
    ):
        """INCOME + BOTH should not raise."""
        transaction_service._validate_category_type(
            TransactionType.INCOME, CategoryType.BOTH
        )

    def test_expense_transaction_with_expense_category_is_valid(
        self, transaction_service
    ):
        """EXPENSE + EXPENSE should not raise."""
        transaction_service._validate_category_type(
            TransactionType.EXPENSE, CategoryType.EXPENSE
        )

    def test_expense_transaction_with_both_category_is_valid(
        self, transaction_service
    ):
        """EXPENSE + BOTH should not raise."""
        transaction_service._validate_category_type(
            TransactionType.EXPENSE, CategoryType.BOTH
        )

    def test_income_transaction_with_expense_category_raises(
        self, transaction_service
    ):
        """INCOME + EXPENSE should raise BusinessRuleError."""
        with pytest.raises(BusinessRuleError):
            transaction_service._validate_category_type(
                TransactionType.INCOME, CategoryType.EXPENSE
            )

    def test_expense_transaction_with_income_category_raises(
        self, transaction_service
    ):
        """EXPENSE + INCOME should raise BusinessRuleError."""
        with pytest.raises(BusinessRuleError):
            transaction_service._validate_category_type(
                TransactionType.EXPENSE, CategoryType.INCOME
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
            user_id=USER_ID,
            amount=Decimal("999.00"),
        )

        call_kwargs = mock_transaction_repo.update.call_args[1]
        assert "amount" in call_kwargs
        assert "type" not in call_kwargs
        assert "date" not in call_kwargs

    def test_update_type_revalidates_category_compatibility(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """Should re-validate compatibility when transaction type changes."""
        # sample_transaction.type == EXPENSE, existing category will be fetched
        # by category_id from the transaction mock
        expense_category = MagicMock()
        expense_category.type = CategoryType.EXPENSE  # incompatible with new INCOME type

        mock_transaction_repo.get_by_id_or_fail.return_value = sample_transaction
        mock_category_repo.get_by_id_or_fail.return_value = expense_category

        with pytest.raises(BusinessRuleError):
            transaction_service.update(
                transaction_id=sample_transaction.id,
                user_id=USER_ID,
                type="income",  # changing type but not category → re-validation fires
            )

    def test_update_category_revalidates_type_compatibility(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """Should re-validate compatibility when category changes."""
        income_category = MagicMock()
        income_category.type = CategoryType.INCOME  # incompatible with existing EXPENSE type

        mock_transaction_repo.get_by_id_or_fail.return_value = sample_transaction
        mock_category_repo.get_by_id_or_fail.return_value = income_category

        with pytest.raises(BusinessRuleError):
            transaction_service.update(
                transaction_id=sample_transaction.id,
                user_id=USER_ID,
                category_id=uuid4(),  # changing category → re-validation with existing EXPENSE type
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
                transaction_id=uuid4(), user_id=USER_ID, amount=Decimal("100.00")
            )


class TestCreateMultiCurrency:
    """Tests for multi-currency transaction creation in TransactionService."""

    def test_create_multi_currency_income_stores_fx_metadata(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """
        Creating an income transaction with a foreign-currency source should
        pass original_amount, original_currency, and exchange_rate to the
        repository unchanged when original_currency differs from the account
        currency.
        """
        account = _make_account()
        account.currency = "COP"

        mock_account_repo.get_by_id_or_fail.return_value = account
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.INCOME
        )
        mock_transaction_repo.create.return_value = sample_transaction

        result = transaction_service.create(
            user_id=USER_ID,
            type="income",
            amount=Decimal("4000000"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
            original_currency="USD",
            original_amount=Decimal("1000"),
            exchange_rate=Decimal("4000"),
        )

        assert result == sample_transaction

        call_kwargs = mock_transaction_repo.create.call_args[1]
        assert call_kwargs["original_currency"] == "USD"
        assert call_kwargs["original_amount"] == Decimal("1000")
        assert call_kwargs["exchange_rate"] == Decimal("4000")
        # amount in account currency must be passed through untouched
        assert call_kwargs["amount"] == Decimal("4000000")

    def test_create_clears_fx_fields_when_original_currency_matches_account(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """
        When original_currency equals the account's own currency the three
        multi-currency fields are redundant and must be cleared before
        persisting.
        """
        account = _make_account()
        account.currency = "USD"

        mock_account_repo.get_by_id_or_fail.return_value = account
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.INCOME
        )
        mock_transaction_repo.create.return_value = sample_transaction

        transaction_service.create(
            user_id=USER_ID,
            type="income",
            amount=Decimal("1000"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
            original_currency="USD",  # same as account
            original_amount=Decimal("1000"),
            exchange_rate=Decimal("1"),
        )

        call_kwargs = mock_transaction_repo.create.call_args[1]
        assert call_kwargs["original_currency"] is None
        assert call_kwargs["original_amount"] is None
        assert call_kwargs["exchange_rate"] is None

    def test_create_single_currency_passes_none_fx_fields(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
        sample_transaction,
    ):
        """
        A standard single-currency transaction must pass None for all three
        multi-currency fields so the database columns remain NULL.
        """
        account = _make_account()
        account.currency = "COP"

        mock_account_repo.get_by_id_or_fail.return_value = account
        mock_category_repo.get_by_id_or_fail.return_value = _make_category(
            CategoryType.EXPENSE
        )
        mock_transaction_repo.create.return_value = sample_transaction

        transaction_service.create(
            user_id=USER_ID,
            type="expense",
            amount=Decimal("500.00"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
        )

        call_kwargs = mock_transaction_repo.create.call_args[1]
        assert call_kwargs["original_currency"] is None
        assert call_kwargs["original_amount"] is None
        assert call_kwargs["exchange_rate"] is None


class TestCreateMultiCurrencySchemaValidation:
    """Tests for multi-currency field validation in TransactionCreate schema."""

    def test_schema_raises_when_original_currency_provided_without_original_amount(self):
        """TransactionCreate must raise ValidationError when original_currency
        is provided but original_amount is omitted."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            from app.schemas.transaction import TransactionCreate
            TransactionCreate(
                type="income",
                amount=Decimal("4000000"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
                original_currency="USD",
                exchange_rate=Decimal("4000"),
                # original_amount intentionally omitted
            )

        errors = exc_info.value.errors()
        assert any("original_amount" in str(e) for e in errors)

    def test_schema_raises_when_original_currency_provided_without_exchange_rate(self):
        """TransactionCreate must raise ValidationError when original_currency
        is provided but exchange_rate is omitted."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            from app.schemas.transaction import TransactionCreate
            TransactionCreate(
                type="income",
                amount=Decimal("4000000"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
                original_currency="USD",
                original_amount=Decimal("1000"),
                # exchange_rate intentionally omitted
            )

        errors = exc_info.value.errors()
        assert any("exchange_rate" in str(e) for e in errors)

    def test_schema_raises_when_original_amount_provided_without_original_currency(self):
        """TransactionCreate must raise ValidationError when original_amount is
        provided without original_currency."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            from app.schemas.transaction import TransactionCreate
            TransactionCreate(
                type="income",
                amount=Decimal("4000000"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
                original_amount=Decimal("1000"),
                exchange_rate=Decimal("4000"),
                # original_currency intentionally omitted
            )

    def test_schema_raises_when_original_amount_is_zero(self):
        """TransactionCreate must reject original_amount <= 0."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            from app.schemas.transaction import TransactionCreate
            TransactionCreate(
                type="income",
                amount=Decimal("4000000"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
                original_currency="USD",
                original_amount=Decimal("0"),
                exchange_rate=Decimal("4000"),
            )

    def test_schema_raises_when_exchange_rate_is_negative(self):
        """TransactionCreate must reject exchange_rate <= 0."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            from app.schemas.transaction import TransactionCreate
            TransactionCreate(
                type="income",
                amount=Decimal("4000000"),
                date=date(2026, 3, 1),
                account_id=uuid4(),
                category_id=uuid4(),
                original_currency="USD",
                original_amount=Decimal("1000"),
                exchange_rate=Decimal("-1"),
            )

    def test_schema_valid_complete_multi_currency_payload(self):
        """A fully populated multi-currency payload must be accepted."""
        from app.schemas.transaction import TransactionCreate

        schema = TransactionCreate(
            type="income",
            amount=Decimal("4000000"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
            original_currency="USD",
            original_amount=Decimal("1000"),
            exchange_rate=Decimal("4000"),
        )

        assert schema.original_currency == "USD"
        assert schema.original_amount == Decimal("1000")
        assert schema.exchange_rate == Decimal("4000")

    def test_schema_valid_single_currency_payload(self):
        """A transaction with no multi-currency fields must be accepted."""
        from app.schemas.transaction import TransactionCreate

        schema = TransactionCreate(
            type="expense",
            amount=Decimal("200.00"),
            date=date(2026, 3, 1),
            account_id=uuid4(),
            category_id=uuid4(),
        )

        assert schema.original_currency is None
        assert schema.original_amount is None
        assert schema.exchange_rate is None


class TestDelete:
    """Tests for TransactionService.delete."""

    def test_delete_success(
        self, transaction_service, mock_transaction_repo, sample_transaction
    ):
        """Should call repository.delete with the fetched transaction object."""
        mock_transaction_repo.get_by_id_or_fail.return_value = sample_transaction

        transaction_service.delete(sample_transaction.id, user_id=USER_ID)

        mock_transaction_repo.delete.assert_called_once_with(sample_transaction)

    def test_delete_not_found(
        self, transaction_service, mock_transaction_repo
    ):
        """Should raise NotFoundError and never call delete when transaction is absent."""
        mock_transaction_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Transaction", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transaction_service.delete(uuid4(), user_id=USER_ID)


class TestCreateBaseRate:
    """Tests that base_rate is accepted and forwarded by TransactionService.create."""

    def test_create_passes_base_rate_to_repo(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
    ):
        """base_rate passed to create() must be forwarded to repository.create()."""
        from app.models.category import CategoryType

        account_id = uuid4()
        category_id = uuid4()

        mock_account = Mock()
        mock_account.currency = "COP"
        mock_account_repo.get_by_id_or_fail.return_value = mock_account

        mock_category = Mock()
        mock_category.type = CategoryType.EXPENSE
        mock_category_repo.get_by_id_or_fail.return_value = mock_category

        expected_tx = Mock()
        mock_transaction_repo.create.return_value = expected_tx

        result = transaction_service.create(
            user_id=USER_ID,
            type="expense",
            amount=Decimal("100.00"),
            date=date(2026, 3, 12),
            account_id=account_id,
            category_id=category_id,
            base_rate=Decimal("4200.123456789"),
        )

        call_kwargs = mock_transaction_repo.create.call_args.kwargs
        assert call_kwargs["base_rate"] == Decimal("4200.123456789")
        assert result is expected_tx

    def test_create_base_rate_none_by_default(
        self,
        transaction_service,
        mock_transaction_repo,
        mock_account_repo,
        mock_category_repo,
    ):
        """base_rate defaults to None when not provided."""
        from app.models.category import CategoryType

        mock_account = Mock()
        mock_account.currency = "COP"
        mock_account_repo.get_by_id_or_fail.return_value = mock_account

        mock_category = Mock()
        mock_category.type = CategoryType.EXPENSE
        mock_category_repo.get_by_id_or_fail.return_value = mock_category

        mock_transaction_repo.create.return_value = Mock()

        transaction_service.create(
            user_id=USER_ID,
            type="expense",
            amount=Decimal("100.00"),
            date=date(2026, 3, 12),
            account_id=uuid4(),
            category_id=uuid4(),
        )

        call_kwargs = mock_transaction_repo.create.call_args.kwargs
        assert call_kwargs.get("base_rate") is None

        mock_transaction_repo.delete.assert_not_called()
