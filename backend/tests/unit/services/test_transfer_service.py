"""
Unit tests for TransferService.

These tests focus on business logic validation using mocked repositories.
No database, no Flask app context, no db.session — pure unit tests.
All service methods now accept user_id — the tests pass a fixed UUID.
"""

import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4
from unittest.mock import Mock, MagicMock, patch

from app.services.transfer import TransferService
from app.models.transfer import Transfer
from app.models.account import Account
from app.utils.exceptions import NotFoundError, BusinessRuleError

USER_ID = uuid4()


# ============================================================================
# LOCAL FIXTURES
# ============================================================================

@pytest.fixture
def mock_transfer_repo():
    """Create a mocked TransferRepository patched at the service module level."""
    with patch('app.services.transfer.TransferRepository') as mock:
        yield mock.return_value


@pytest.fixture
def mock_account_repo():
    """Create a mocked AccountRepository patched at the service module level."""
    with patch('app.services.transfer.AccountRepository') as mock:
        yield mock.return_value


@pytest.fixture
def transfer_service(mock_transfer_repo, mock_account_repo):
    """
    Create a TransferService instance with all repository dependencies mocked.

    Both patch fixtures must be active before TransferService() is instantiated
    so that __init__ receives mocked classes. After construction the repository
    attributes are overwritten with the mock instances for deterministic access.
    """
    service = TransferService()
    service.repository = mock_transfer_repo
    service.account_repository = mock_account_repo
    return service


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestGetById:
    """Tests for TransferService.get_by_id."""

    def test_get_by_id_success(self, transfer_service, mock_transfer_repo, mock_transfer):
        """Should return the transfer when the repository finds it."""
        mock_transfer_repo.get_with_relations.return_value = mock_transfer

        result = transfer_service.get_by_id(mock_transfer.id, user_id=USER_ID)

        mock_transfer_repo.get_with_relations.assert_called_once_with(
            mock_transfer.id, USER_ID
        )
        assert result == mock_transfer

    def test_get_by_id_not_found(self, transfer_service, mock_transfer_repo):
        """Should raise NotFoundError when the repository returns None."""
        transfer_id = uuid4()
        mock_transfer_repo.get_with_relations.return_value = None

        with pytest.raises(NotFoundError):
            transfer_service.get_by_id(transfer_id, user_id=USER_ID)


class TestGetFiltered:
    """Tests for TransferService.get_filtered."""

    def test_get_filtered_pagination_offset_calculated(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Should compute offset = (page - 1) * limit before querying."""
        mock_transfer_repo.get_filtered.return_value = ([mock_transfer], 1)

        result, total = transfer_service.get_filtered(
            user_id=USER_ID, page=3, limit=10
        )

        call_kwargs = mock_transfer_repo.get_filtered.call_args.kwargs
        assert call_kwargs["offset"] == 20  # (3-1) * 10
        assert call_kwargs["limit"] == 10
        assert total == 1

    def test_get_filtered_first_page_offset_zero(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Offset should be 0 for the first page."""
        mock_transfer_repo.get_filtered.return_value = ([mock_transfer], 1)

        transfer_service.get_filtered(user_id=USER_ID, page=1, limit=20)

        call_kwargs = mock_transfer_repo.get_filtered.call_args.kwargs
        assert call_kwargs["offset"] == 0


class TestCreate:
    """Tests for TransferService.create."""

    def test_create_valid_transfer(
        self, transfer_service, mock_transfer_repo, mock_account_repo, mock_transfer
    ):
        """Should create and return a transfer when both accounts share the same currency."""
        origin = MagicMock()
        origin.currency = "MXN"
        destination = MagicMock()
        destination.currency = "MXN"

        mock_account_repo.get_by_id_or_fail.side_effect = [origin, destination]
        mock_transfer_repo.create.return_value = mock_transfer

        result = transfer_service.create(
            user_id=USER_ID,
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("500.00"),
            date=date(2026, 3, 1),
        )

        assert result == mock_transfer
        mock_transfer_repo.create.assert_called_once()

    def test_create_cross_currency_missing_destination_amount_raises(
        self, transfer_service, mock_account_repo
    ):
        """Cross-currency transfer without destination_amount should raise ValidationError."""
        from app.utils.exceptions import ValidationError
        origin = MagicMock()
        origin.currency = "MXN"
        destination = MagicMock()
        destination.currency = "USD"

        mock_account_repo.get_by_id_or_fail.side_effect = [origin, destination]

        with pytest.raises(ValidationError):
            transfer_service.create(
                user_id=USER_ID,
                source_account_id=uuid4(),
                destination_account_id=uuid4(),
                amount=Decimal("500.00"),
                date=date(2026, 3, 1),
                # Missing destination_amount and exchange_rate
            )

    def test_create_cross_currency_success(
        self, transfer_service, mock_transfer_repo, mock_account_repo, mock_transfer
    ):
        """Cross-currency transfer with all required fields should succeed."""
        origin = MagicMock()
        origin.currency = "USD"
        destination = MagicMock()
        destination.currency = "COP"

        mock_account_repo.get_by_id_or_fail.side_effect = [origin, destination]
        mock_transfer_repo.get_by_offline_id.return_value = None
        mock_transfer_repo.create.return_value = mock_transfer

        result = transfer_service.create(
            user_id=USER_ID,
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("100.00"),
            destination_amount=Decimal("420000.00"),
            exchange_rate=Decimal("4200.00"),
            date=date(2026, 3, 1),
        )

        assert result == mock_transfer
        mock_transfer_repo.create.assert_called_once()

    def test_create_idempotency_returns_existing_record(
        self, transfer_service, mock_transfer_repo, mock_account_repo, mock_transfer
    ):
        """Should return the existing transfer immediately when offline_id matches a record."""
        offline_id = "client-uuid-abc123"
        mock_transfer_repo.get_by_offline_id.return_value = mock_transfer

        result = transfer_service.create(
            user_id=USER_ID,
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("500.00"),
            date=date(2026, 3, 1),
            offline_id=offline_id,
        )

        assert result == mock_transfer
        # Must short-circuit: no account lookups, no creation
        mock_account_repo.get_by_id_or_fail.assert_not_called()
        mock_transfer_repo.create.assert_not_called()

    def test_create_source_account_not_found(
        self, transfer_service, mock_account_repo
    ):
        """Should propagate NotFoundError when the source account does not exist."""
        mock_account_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Account", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transfer_service.create(
                user_id=USER_ID,
                source_account_id=uuid4(),
                destination_account_id=uuid4(),
                amount=Decimal("100.00"),
                date=date(2026, 3, 1),
            )

    def test_create_destination_account_not_found(
        self, transfer_service, mock_account_repo
    ):
        """Should raise NotFoundError when the destination account does not exist."""
        origin = MagicMock()
        origin.currency = "MXN"
        mock_account_repo.get_by_id_or_fail.side_effect = [
            origin,
            NotFoundError("Account", str(uuid4())),
        ]

        with pytest.raises(NotFoundError):
            transfer_service.create(
                user_id=USER_ID,
                source_account_id=uuid4(),
                destination_account_id=uuid4(),
                amount=Decimal("100.00"),
                date=date(2026, 3, 1),
            )


class TestUpdate:
    """Tests for TransferService.update."""

    def test_update_partial_fields(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Should include only the provided fields in the repository update call."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer
        mock_transfer_repo.update.return_value = mock_transfer

        transfer_service.update(
            transfer_id=mock_transfer.id,
            user_id=USER_ID,
            amount=Decimal("999.00"),
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert "amount" in call_kwargs
        assert "date" not in call_kwargs
        assert "description" not in call_kwargs

    def test_update_cannot_change_accounts(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Account IDs must never appear in the repository update payload."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer
        mock_transfer_repo.update.return_value = mock_transfer

        transfer_service.update(
            transfer_id=mock_transfer.id,
            user_id=USER_ID,
            description="Updated description",
            tags=["new-tag"],
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert "source_account_id" not in call_kwargs
        assert "destination_account_id" not in call_kwargs

    def test_update_all_allowed_fields(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Should pass all four updatable fields when all are provided."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer
        mock_transfer_repo.update.return_value = mock_transfer

        transfer_service.update(
            transfer_id=mock_transfer.id,
            user_id=USER_ID,
            amount=Decimal("750.00"),
            date=date(2026, 4, 1),
            description="Nueva descripción",
            tags=["tag1", "tag2"],
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert call_kwargs["amount"] == Decimal("750.00")
        assert call_kwargs["date"] == date(2026, 4, 1)
        assert call_kwargs["description"] == "Nueva descripción"
        assert call_kwargs["tags"] == ["tag1", "tag2"]

    def test_update_not_found(self, transfer_service, mock_transfer_repo):
        """Should raise NotFoundError when the transfer does not exist."""
        mock_transfer_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Transfer", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transfer_service.update(
                transfer_id=uuid4(), user_id=USER_ID, amount=Decimal("100.00")
            )


class TestDelete:
    """Tests for TransferService.delete."""

    def test_delete_success(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Should call repository.delete with the fetched transfer object."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer

        transfer_service.delete(mock_transfer.id, user_id=USER_ID)

        mock_transfer_repo.delete.assert_called_once_with(mock_transfer)

    def test_delete_not_found(self, transfer_service, mock_transfer_repo):
        """Should raise NotFoundError and never call delete when transfer is absent."""
        mock_transfer_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Transfer", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transfer_service.delete(uuid4(), user_id=USER_ID)


class TestCreateTitle:
    """Tests that title is accepted and forwarded by TransferService.create."""

    def test_create_passes_title_to_repo(
        self,
        transfer_service,
        mock_transfer_repo,
        mock_account_repo,
    ):
        """title passed to create() must be forwarded to repository.create()."""
        mock_source = Mock()
        mock_source.currency = "MXN"
        mock_dest = Mock()
        mock_dest.currency = "MXN"
        mock_account_repo.get_by_id_or_fail.side_effect = [mock_source, mock_dest]
        mock_transfer_repo.create.return_value = Mock()

        transfer_service.create(
            user_id=USER_ID,
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("500.00"),
            date=date(2026, 3, 1),
            title="Pago de renta",
        )

        call_kwargs = mock_transfer_repo.create.call_args.kwargs
        assert "title" in call_kwargs, "title must be present in repository.create() call"
        assert call_kwargs["title"] == "Pago de renta"

    def test_create_title_none_by_default(
        self,
        transfer_service,
        mock_transfer_repo,
        mock_account_repo,
    ):
        """title defaults to None when not provided."""
        mock_source = Mock()
        mock_source.currency = "USD"
        mock_dest = Mock()
        mock_dest.currency = "USD"
        mock_account_repo.get_by_id_or_fail.side_effect = [mock_source, mock_dest]
        mock_transfer_repo.create.return_value = Mock()

        transfer_service.create(
            user_id=USER_ID,
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("100.00"),
            date=date(2026, 3, 1),
        )

        call_kwargs = mock_transfer_repo.create.call_args.kwargs
        assert call_kwargs.get("title") is None


class TestUpdateTitle:
    """Tests that title is accepted and forwarded by TransferService.update."""

    def test_update_passes_title_to_repo(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """title passed to update() must be included in the repository update payload."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer
        mock_transfer_repo.update.return_value = mock_transfer

        transfer_service.update(
            transfer_id=mock_transfer.id,
            user_id=USER_ID,
            title="Nuevo título",
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert call_kwargs["title"] == "Nuevo título"

    def test_update_title_none_not_included(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """title=None must NOT be included in the update payload (no-op)."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer
        mock_transfer_repo.update.return_value = mock_transfer

        transfer_service.update(
            transfer_id=mock_transfer.id,
            user_id=USER_ID,
            description="Solo descripción",
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert "title" not in call_kwargs


class TestCreateBaseRate:
    """Tests that base_rate is accepted and forwarded by TransferService.create."""

    def test_create_passes_base_rate_to_repo(
        self,
        transfer_service,
        mock_transfer_repo,
        mock_account_repo,
    ):
        """base_rate passed to create() must be forwarded to repository.create()."""
        source_id = uuid4()
        dest_id = uuid4()

        mock_source = Mock()
        mock_source.currency = "COP"
        mock_dest = Mock()
        mock_dest.currency = "COP"
        mock_account_repo.get_by_id_or_fail.side_effect = [mock_source, mock_dest]

        expected_transfer = Mock()
        mock_transfer_repo.create.return_value = expected_transfer

        result = transfer_service.create(
            user_id=USER_ID,
            source_account_id=source_id,
            destination_account_id=dest_id,
            amount=Decimal("500.00"),
            date=date(2026, 3, 12),
            base_rate=Decimal("4200.123456789"),
        )

        call_kwargs = mock_transfer_repo.create.call_args.kwargs
        assert call_kwargs["base_rate"] == Decimal("4200.123456789")
        assert result is expected_transfer

    def test_create_base_rate_none_by_default(
        self,
        transfer_service,
        mock_transfer_repo,
        mock_account_repo,
    ):
        """base_rate defaults to None when not provided."""
        mock_source = Mock()
        mock_source.currency = "USD"
        mock_dest = Mock()
        mock_dest.currency = "USD"
        mock_account_repo.get_by_id_or_fail.side_effect = [mock_source, mock_dest]
        mock_transfer_repo.create.return_value = Mock()

        transfer_service.create(
            user_id=USER_ID,
            source_account_id=uuid4(),
            destination_account_id=uuid4(),
            amount=Decimal("100.00"),
            date=date(2026, 3, 12),
        )

        call_kwargs = mock_transfer_repo.create.call_args.kwargs
        assert call_kwargs.get("base_rate") is None

        mock_transfer_repo.delete.assert_not_called()
