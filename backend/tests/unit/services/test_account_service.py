"""
Unit tests for AccountService.

These tests focus on business logic validation using mocked repositories.
All service methods now accept user_id — the tests pass a fixed UUID.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, MagicMock

from app.services.account import AccountService
from app.models.account import Account, AccountType
from app.utils.exceptions import NotFoundError, BusinessRuleError


# Shared user_id used across all tests
USER_ID = uuid4()


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
    account = MagicMock()
    account.id = uuid4()
    account.name = "Cuenta Test"
    account.type = AccountType.DEBIT
    account.currency = "MXN"
    account.description = "Descripción test"
    account.tags = ["test"]
    account.active = True

    # Mock relationships for delete validation
    account.transactions = Mock()
    account.transactions.count.return_value = 0
    account.transfers_source = Mock()
    account.transfers_source.count.return_value = 0
    account.transfers_destination = Mock()
    account.transfers_destination.count.return_value = 0

    return account


class TestGetAll:
    """Tests for get_all method."""

    def test_get_all_active_only(self, account_service, mock_repository, sample_account):
        """Should return only active accounts by default."""
        mock_repository.get_all_active.return_value = [sample_account]

        result = account_service.get_all(user_id=USER_ID)

        mock_repository.get_all_active.assert_called_once_with(user_id=USER_ID)
        mock_repository.get_all.assert_not_called()
        assert len(result) == 1
        assert result[0] == sample_account

    def test_get_all_including_archived(self, account_service, mock_repository, sample_account):
        """Should return all accounts including archived when requested."""
        archived_account = MagicMock()
        archived_account.active = False
        mock_repository.get_all.return_value = [sample_account, archived_account]

        result = account_service.get_all(user_id=USER_ID, include_archived=True)

        mock_repository.get_all.assert_called_once_with(user_id=USER_ID, include_archived=True)
        mock_repository.get_all_active.assert_not_called()
        assert len(result) == 2

    def test_get_all_with_updated_since_forwards_to_repository(
        self, account_service, mock_repository, sample_account
    ):
        """get_all with updated_since must forward the parameter to the repository."""
        cutoff = datetime(2026, 1, 15, 12, 0, 0)
        mock_repository.get_all.return_value = [sample_account]

        result = account_service.get_all(
            user_id=USER_ID, include_archived=True, updated_since=cutoff
        )

        mock_repository.get_all.assert_called_once_with(
            user_id=USER_ID, include_archived=True, updated_since=cutoff
        )
        assert len(result) == 1


class TestGetById:
    """Tests for get_by_id method."""

    def test_get_by_id_success(self, account_service, mock_repository, sample_account):
        """Should return account when found."""
        mock_repository.get_by_id_or_fail.return_value = sample_account

        result = account_service.get_by_id(sample_account.id, user_id=USER_ID)

        mock_repository.get_by_id_or_fail.assert_called_once_with(sample_account.id, USER_ID)
        assert result == sample_account

    def test_get_by_id_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account", "test-id")

        with pytest.raises(NotFoundError):
            account_service.get_by_id(account_id, user_id=USER_ID)


class TestCreate:
    """Tests for create method."""

    def test_create_account_success(self, account_service, mock_repository):
        """Should create account with provided data."""
        new_account = MagicMock()
        mock_repository.create.return_value = new_account

        result = account_service.create(
            user_id=USER_ID,
            name="Nueva Cuenta",
            type="debit",
            currency="usd",
            description="Test description",
            tags=["tag1", "tag2"]
        )

        assert result == new_account
        mock_repository.create.assert_called_once()
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["user_id"] == USER_ID
        assert call_kwargs["name"] == "Nueva Cuenta"
        assert call_kwargs["type"] == AccountType.DEBIT
        assert call_kwargs["currency"] == "USD"
        assert call_kwargs["tags"] == ["tag1", "tag2"]

    def test_create_account_minimal_data(self, account_service, mock_repository):
        """Should create account with only required fields."""
        new_account = MagicMock()
        mock_repository.create.return_value = new_account

        result = account_service.create(
            user_id=USER_ID,
            name="Cuenta Mínima",
            type="cash",
            currency="MXN"
        )

        assert result == new_account
        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["description"] is None
        assert call_kwargs["tags"] == []

    def test_create_account_currency_uppercase(self, account_service, mock_repository):
        """Should convert currency code to uppercase."""
        mock_repository.create.return_value = MagicMock()

        account_service.create(
            user_id=USER_ID,
            name="Test",
            type="debit",
            currency="eur"
        )

        call_kwargs = mock_repository.create.call_args.kwargs
        assert call_kwargs["currency"] == "EUR"


class TestUpdate:
    """Tests for update method."""

    def test_update_account_success(self, account_service, mock_repository, sample_account):
        """Should update account with provided data."""
        updated_account = MagicMock()
        mock_repository.get_by_id_or_fail.return_value = sample_account
        mock_repository.update.return_value = updated_account

        result = account_service.update(
            account_id=sample_account.id,
            user_id=USER_ID,
            name="Nombre Actualizado",
            currency="USD"
        )

        assert result == updated_account
        mock_repository.update.assert_called_once()
        call_args = mock_repository.update.call_args
        assert call_args[0][0] == sample_account
        assert call_args[1]["name"] == "Nombre Actualizado"
        assert call_args[1]["currency"] == "USD"

    def test_update_account_partial(self, account_service, mock_repository, sample_account):
        """Should only update provided fields."""
        mock_repository.get_by_id_or_fail.return_value = sample_account
        mock_repository.update.return_value = sample_account

        account_service.update(
            account_id=sample_account.id,
            user_id=USER_ID,
            name="Nuevo Nombre"
        )

        call_kwargs = mock_repository.update.call_args[1]
        assert "name" in call_kwargs
        assert "type" not in call_kwargs
        assert "currency" not in call_kwargs

    def test_update_account_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account", "test-id")

        with pytest.raises(NotFoundError):
            account_service.update(account_id, user_id=USER_ID, name="Test")


class TestArchive:
    """Tests for archive method (soft delete)."""

    def test_archive_success(self, account_service, mock_repository, sample_account):
        """Should archive account successfully."""
        archived_account = MagicMock()
        archived_account.active = False
        mock_repository.soft_delete.return_value = archived_account

        result = account_service.archive(sample_account.id, user_id=USER_ID)

        assert result == archived_account
        mock_repository.soft_delete.assert_called_once_with(sample_account.id, USER_ID)

    def test_archive_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.soft_delete.side_effect = NotFoundError("Account", "test-id")

        with pytest.raises(NotFoundError):
            account_service.archive(account_id, user_id=USER_ID)


class TestDelete:
    """Tests for delete method (hard delete with validations).

    delete() uses db.session.execute() directly (SA 2.0 pattern, replacing
    deprecated lazy="dynamic" .count()). We patch db.session.execute so
    unit tests don't need an app context or a real DB connection.
    """

    def _make_execute_mock(self, txn_count: int, transfer_count: int):
        """Return a side_effect function that returns mock scalars for the two count queries."""
        call_results = [txn_count, transfer_count]
        call_iter = iter(call_results)

        def execute_side_effect(*args, **kwargs):
            mock_result = Mock()
            mock_result.scalar.return_value = next(call_iter)
            return mock_result

        return execute_side_effect

    def test_delete_success(self, account_service, mock_repository, sample_account):
        """Should delete account when no transactions or transfers exist."""
        mock_repository.get_by_id_or_fail.return_value = sample_account

        with patch('app.services.account.db') as mock_db:
            mock_db.session.execute.side_effect = self._make_execute_mock(0, 0)
            account_service.delete(sample_account.id, user_id=USER_ID)

        mock_repository.delete.assert_called_once_with(sample_account)

    def test_delete_with_transactions_fails(self, account_service, mock_repository, sample_account):
        """Should raise BusinessRuleError when account has transactions."""
        mock_repository.get_by_id_or_fail.return_value = sample_account

        with patch('app.services.account.db') as mock_db:
            mock_db.session.execute.side_effect = self._make_execute_mock(5, 0)
            with pytest.raises(BusinessRuleError) as exc_info:
                account_service.delete(sample_account.id, user_id=USER_ID)

        assert "transacciones" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_with_transfers_source_fails(self, account_service, mock_repository, sample_account):
        """Should raise BusinessRuleError when account has outgoing transfers."""
        mock_repository.get_by_id_or_fail.return_value = sample_account

        with patch('app.services.account.db') as mock_db:
            mock_db.session.execute.side_effect = self._make_execute_mock(0, 3)
            with pytest.raises(BusinessRuleError) as exc_info:
                account_service.delete(sample_account.id, user_id=USER_ID)

        assert "transferencias" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_with_transfers_destination_fails(self, account_service, mock_repository, sample_account):
        """Should raise BusinessRuleError when account has incoming transfers."""
        mock_repository.get_by_id_or_fail.return_value = sample_account

        with patch('app.services.account.db') as mock_db:
            mock_db.session.execute.side_effect = self._make_execute_mock(0, 2)
            with pytest.raises(BusinessRuleError) as exc_info:
                account_service.delete(sample_account.id, user_id=USER_ID)

        assert "transferencias" in str(exc_info.value).lower()
        mock_repository.delete.assert_not_called()

    def test_delete_not_found(self, account_service, mock_repository):
        """Should raise NotFoundError when account doesn't exist."""
        account_id = uuid4()
        mock_repository.get_by_id_or_fail.side_effect = NotFoundError("Account", "test-id")

        with pytest.raises(NotFoundError):
            account_service.delete(account_id, user_id=USER_ID)


