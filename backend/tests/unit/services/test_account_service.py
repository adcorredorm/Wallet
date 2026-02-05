"""
Unit tests for AccountService.

These tests focus on business logic validation using mocked repositories.
"""

import pytest
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

from app.services.account import AccountService
from app.models.account import Account, AccountType
from app.utils.exceptions import NotFoundError, BusinessRuleError


@pytest.fixture
def mock_repository():
    """Create a mocked AccountRepository."""
    with patch('app.services.account.AccountRepository') as mock:
        yield mock.return_value


@pytest.fixture
def account_service(mock_repository):
    """Create AccountService instance with mocked repository."""
    service = AccountService()
    service.repository = mock_repository
    return service


@pytest.fixture
def sample_account():
    """Create a sample account for testing."""
    account = Mock(spec=Account)
    account.id = uuid4()
    account.nombre = "Cuenta Test"
    account.tipo = AccountType.DEBITO
    account.divisa = "MXN"
    account.descripcion = "Descripción test"
    account.tags = ["test"]
    account.activa = True

    # Mock relationships for delete validation
    account.transacciones = Mock()
    account.transacciones.count.return_value = 0
    account.transferencias_origen = Mock()
    account.transferencias_origen.count.return_value = 0
    account.transferencias_destino = Mock()
    account.transferencias_destino.count.return_value = 0

    return account


class TestGetAll:
    """Tests for get_all method."""

    def test_get_all_active_only(self, account_service, mock_repository, sample_account):
        """Should return only active accounts by default."""
        mock_repository.get_all_active.return_value = [sample_account]

        result = account_service.get_all()

        mock_repository.get_all_active.assert_called_once()
        mock_repository.get_all.assert_not_called()
        assert len(result) == 1
        assert result[0] == sample_account

    def test_get_all_including_archived(self, account_service, mock_repository, sample_account):
        """Should return all accounts including archived when requested."""
        archived_account = Mock(spec=Account)
        archived_account.activa = False
        mock_repository.get_all.return_value = [sample_account, archived_account]

        result = account_service.get_all(include_archived=True)

        mock_repository.get_all.assert_called_once()
        mock_repository.get_all_active.assert_not_called()
        assert len(result) == 2


class TestGetById:
    """Tests for get_by_id method."""

    def test_get_by_id_success(self, account_service, mock_repository, sample_account):
        """Should return account when found."""
        mock_repository.get_by_id_or_fail.return_value = sample_account

        result = account_service.get_by_id(sample_account.id)

        mock_repository.get_by_id_or_fail.assert_called_once_with(sample_account.id)
        assert result == sample_account

    def test_get_by_id_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account not found")

        with pytest.raises(NotFoundError):
            account_service.get_by_id(account_id)


class TestGetWithBalance:
    """Tests for get_with_balance method."""

    def test_get_with_balance_success(self, account_service, mock_repository, sample_account):
        """Should return account and its calculated balance."""
        expected_balance = Decimal("1500.50")
        mock_repository.get_by_id_or_fail.return_value = sample_account
        mock_repository.calculate_balance.return_value = expected_balance

        account, balance = account_service.get_with_balance(sample_account.id)

        assert account == sample_account
        assert balance == expected_balance
        mock_repository.calculate_balance.assert_called_once_with(sample_account.id)

    def test_get_with_balance_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account not found")

        with pytest.raises(NotFoundError):
            account_service.get_with_balance(account_id)


class TestGetAllWithBalances:
    """Tests for get_all_with_balances method."""

    def test_get_all_with_balances(self, account_service, mock_repository):
        """Should return all accounts with their balances."""
        account1 = Mock(spec=Account)
        account1.id = uuid4()
        account2 = Mock(spec=Account)
        account2.id = uuid4()

        mock_repository.get_all_active.return_value = [account1, account2]
        mock_repository.calculate_balance.side_effect = [
            Decimal("1000.00"),
            Decimal("2000.00")
        ]

        result = account_service.get_all_with_balances()

        assert len(result) == 2
        assert result[0] == (account1, Decimal("1000.00"))
        assert result[1] == (account2, Decimal("2000.00"))
        assert mock_repository.calculate_balance.call_count == 2


class TestCreate:
    """Tests for create method."""

    def test_create_account_success(self, account_service, mock_repository):
        """Should create account with provided data."""
        new_account = Mock(spec=Account)
        mock_repository.create.return_value = new_account

        result = account_service.create(
            nombre="Nueva Cuenta",
            tipo="debito",
            divisa="usd",  # Should be converted to uppercase
            descripcion="Test description",
            tags=["tag1", "tag2"]
        )

        assert result == new_account
        mock_repository.create.assert_called_once()
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["nombre"] == "Nueva Cuenta"
        assert call_kwargs["tipo"] == AccountType.DEBITO
        assert call_kwargs["divisa"] == "USD"  # Uppercase
        assert call_kwargs["tags"] == ["tag1", "tag2"]

    def test_create_account_minimal_data(self, account_service, mock_repository):
        """Should create account with only required fields."""
        new_account = Mock(spec=Account)
        mock_repository.create.return_value = new_account

        result = account_service.create(
            nombre="Cuenta Mínima",
            tipo="efectivo",
            divisa="MXN"
        )

        assert result == new_account
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["descripcion"] is None
        assert call_kwargs["tags"] == []

    def test_create_account_divisa_uppercase(self, account_service, mock_repository):
        """Should convert currency code to uppercase."""
        mock_repository.create.return_value = Mock(spec=Account)

        account_service.create(
            nombre="Test",
            tipo="debito",
            divisa="eur"
        )

        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["divisa"] == "EUR"


class TestUpdate:
    """Tests for update method."""

    def test_update_account_success(self, account_service, mock_repository, sample_account):
        """Should update account with provided data."""
        updated_account = Mock(spec=Account)
        mock_repository.get_by_id_or_fail.return_value = sample_account
        mock_repository.update.return_value = updated_account

        result = account_service.update(
            account_id=sample_account.id,
            nombre="Nombre Actualizado",
            divisa="USD"
        )

        assert result == updated_account
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args
        assert call_args[0][0] == sample_account
        assert call_args[1]["nombre"] == "Nombre Actualizado"
        assert call_args[1]["divisa"] == "USD"

    def test_update_account_partial(self, account_service, mock_repository, sample_account):
        """Should only update provided fields."""
        mock_repository.get_by_id_or_fail.return_value = sample_account
        mock_repository.update.return_value = sample_account

        account_service.update(
            account_id=sample_account.id,
            nombre="Nuevo Nombre"
        )

        call_kwargs = mock_repository.update.call_args[1]
        assert "nombre" in call_kwargs
        assert "tipo" not in call_kwargs
        assert "divisa" not in call_kwargs

    def test_update_account_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account not found")

        with pytest.raises(NotFoundError):
            account_service.update(account_id, nombre="Test")


class TestArchive:
    """Tests for archive method (soft delete)."""

    def test_archive_success(self, account_service, mock_repository, sample_account):
        """Should archive account successfully."""
        archived_account = Mock(spec=Account)
        archived_account.activa = False
        mock_repository.soft_delete.return_value = archived_account

        result = account_service.archive(sample_account.id)

        assert result == archived_account
        mock_repository.soft_delete.assert_called_once_with(sample_account.id)

    def test_archive_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.soft_delete.side_effect = NotFoundError("Account not found")

        with pytest.raises(NotFoundError):
            account_service.archive(account_id)


class TestDelete:
    """Tests for delete method (hard delete with validations)."""

    def test_delete_success(self, account_service, mock_repository, sample_account):
        """Should delete account when no transactions or transfers exist."""
        mock_repository.get_by_id_or_fail.return_value = sample_account

        account_service.delete(sample_account.id)

        mock_repository.delete.assert_called_once_with(sample_account)

    def test_delete_with_transactions_fails(self, account_service, mock_repository, sample_account):
        """Should raise BusinessRuleError when account has transactions."""
        sample_account.transacciones.count.return_value = 5
        mock_repository.get_by_id_or_fail.return_value = sample_account

        with pytest.raises(BusinessRuleError) as exc_info:
            account_service.delete(sample_account.id)

        assert "transacciones" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_with_transfers_origen_fails(self, account_service, mock_repository, sample_account):
        """Should raise BusinessRuleError when account has outgoing transfers."""
        sample_account.transferencias_origen.count.return_value = 3
        mock_repository.get_by_id_or_fail.return_value = sample_account

        with pytest.raises(BusinessRuleError) as exc_info:
            account_service.delete(sample_account.id)

        assert "transferencias" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_with_transfers_destino_fails(self, account_service, mock_repository, sample_account):
        """Should raise BusinessRuleError when account has incoming transfers."""
        sample_account.transferencias_destino.count.return_value = 2
        mock_repository.get_by_id_or_fail.return_value = sample_account

        with pytest.raises(BusinessRuleError) as exc_info:
            account_service.delete(sample_account.id)

        assert "transferencias" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account not found")

        with pytest.raises(NotFoundError):
            account_service.delete(account_id)


class TestGetBalance:
    """Tests for get_balance method."""

    def test_get_balance_success(self, account_service, mock_repository, sample_account):
        """Should return calculated balance for account."""
        expected_balance = Decimal("2500.75")
        mock_repository.get_by_id_or_fail.return_value = sample_account
        mock_repository.calculate_balance.return_value = expected_balance

        result = account_service.get_balance(sample_account.id)

        assert result == expected_balance
        mock_repository.get_by_id_or_fail.assert_called_once_with(sample_account.id)
        mock_repository.calculate_balance.assert_called_once_with(sample_account.id)

    def test_get_balance_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account not found")

        with pytest.raises(NotFoundError):
            account_service.get_balance(account_id)

        mock_repository.calculate_balance.assert_not_called()
