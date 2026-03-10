"""
Unit tests for TransferService.

These tests focus on business logic validation using mocked repositories.
No database, no Flask app context, no db.session — pure unit tests.
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

        result = transfer_service.get_by_id(mock_transfer.id)

        mock_transfer_repo.get_with_relations.assert_called_once_with(mock_transfer.id)
        assert result == mock_transfer

    def test_get_by_id_not_found(self, transfer_service, mock_transfer_repo):
        """Should raise NotFoundError when the repository returns None."""
        transfer_id = uuid4()
        mock_transfer_repo.get_with_relations.return_value = None

        with pytest.raises(NotFoundError):
            transfer_service.get_by_id(transfer_id)


class TestGetFiltered:
    """Tests for TransferService.get_filtered."""

    def test_get_filtered_pagination_offset_calculated(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Should compute offset = (page - 1) * limit before querying."""
        mock_transfer_repo.get_filtered.return_value = ([mock_transfer], 1)

        result, total = transfer_service.get_filtered(page=3, limit=10)

        call_kwargs = mock_transfer_repo.get_filtered.call_args.kwargs
        assert call_kwargs["offset"] == 20  # (3-1) * 10
        assert call_kwargs["limit"] == 10
        assert total == 1

    def test_get_filtered_first_page_offset_zero(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Offset should be 0 for the first page."""
        mock_transfer_repo.get_filtered.return_value = ([mock_transfer], 1)

        transfer_service.get_filtered(page=1, limit=20)

        call_kwargs = mock_transfer_repo.get_filtered.call_args.kwargs
        assert call_kwargs["offset"] == 0


class TestCreate:
    """Tests for TransferService.create."""

    def test_create_valid_transfer(
        self, transfer_service, mock_transfer_repo, mock_account_repo, mock_transfer
    ):
        """Should create and return a transfer when both accounts share the same currency."""
        origin = MagicMock()
        origin.divisa = "MXN"
        destination = MagicMock()
        destination.divisa = "MXN"

        mock_account_repo.get_by_id_or_fail.side_effect = [origin, destination]
        mock_transfer_repo.create.return_value = mock_transfer

        result = transfer_service.create(
            cuenta_origen_id=uuid4(),
            cuenta_destino_id=uuid4(),
            monto=Decimal("500.00"),
            fecha=date(2026, 3, 1),
        )

        assert result == mock_transfer
        mock_transfer_repo.create.assert_called_once()

    def test_create_different_currencies_raises_business_rule_error(
        self, transfer_service, mock_account_repo
    ):
        """Should raise BusinessRuleError when the two accounts have different currencies."""
        origin = MagicMock()
        origin.divisa = "MXN"
        destination = MagicMock()
        destination.divisa = "USD"

        mock_account_repo.get_by_id_or_fail.side_effect = [origin, destination]

        with pytest.raises(BusinessRuleError) as exc_info:
            transfer_service.create(
                cuenta_origen_id=uuid4(),
                cuenta_destino_id=uuid4(),
                monto=Decimal("500.00"),
                fecha=date(2026, 3, 1),
            )

        assert "divisas" in str(exc_info.value).lower()

    def test_create_idempotency_returns_existing_record(
        self, transfer_service, mock_transfer_repo, mock_account_repo, mock_transfer
    ):
        """Should return the existing transfer immediately when client_id matches a record."""
        client_id = "client-uuid-abc123"
        mock_transfer_repo.get_by_client_id.return_value = mock_transfer

        result = transfer_service.create(
            cuenta_origen_id=uuid4(),
            cuenta_destino_id=uuid4(),
            monto=Decimal("500.00"),
            fecha=date(2026, 3, 1),
            client_id=client_id,
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
                cuenta_origen_id=uuid4(),
                cuenta_destino_id=uuid4(),
                monto=Decimal("100.00"),
                fecha=date(2026, 3, 1),
            )

    def test_create_destination_account_not_found(
        self, transfer_service, mock_account_repo
    ):
        """Should raise NotFoundError when the destination account does not exist."""
        origin = MagicMock()
        origin.divisa = "MXN"
        mock_account_repo.get_by_id_or_fail.side_effect = [
            origin,
            NotFoundError("Account", str(uuid4())),
        ]

        with pytest.raises(NotFoundError):
            transfer_service.create(
                cuenta_origen_id=uuid4(),
                cuenta_destino_id=uuid4(),
                monto=Decimal("100.00"),
                fecha=date(2026, 3, 1),
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
            monto=Decimal("999.00"),
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert "monto" in call_kwargs
        assert "fecha" not in call_kwargs
        assert "descripcion" not in call_kwargs

    def test_update_cannot_change_accounts(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Account IDs must never appear in the repository update payload."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer
        mock_transfer_repo.update.return_value = mock_transfer

        transfer_service.update(
            transfer_id=mock_transfer.id,
            descripcion="Updated description",
            tags=["new-tag"],
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert "cuenta_origen_id" not in call_kwargs
        assert "cuenta_destino_id" not in call_kwargs

    def test_update_all_allowed_fields(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Should pass all four updatable fields when all are provided."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer
        mock_transfer_repo.update.return_value = mock_transfer

        transfer_service.update(
            transfer_id=mock_transfer.id,
            monto=Decimal("750.00"),
            fecha=date(2026, 4, 1),
            descripcion="Nueva descripción",
            tags=["tag1", "tag2"],
        )

        call_kwargs = mock_transfer_repo.update.call_args[1]
        assert call_kwargs["monto"] == Decimal("750.00")
        assert call_kwargs["fecha"] == date(2026, 4, 1)
        assert call_kwargs["descripcion"] == "Nueva descripción"
        assert call_kwargs["tags"] == ["tag1", "tag2"]

    def test_update_not_found(self, transfer_service, mock_transfer_repo):
        """Should raise NotFoundError when the transfer does not exist."""
        mock_transfer_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Transfer", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transfer_service.update(transfer_id=uuid4(), monto=Decimal("100.00"))


class TestDelete:
    """Tests for TransferService.delete."""

    def test_delete_success(
        self, transfer_service, mock_transfer_repo, mock_transfer
    ):
        """Should call repository.delete with the fetched transfer object."""
        mock_transfer_repo.get_by_id_or_fail.return_value = mock_transfer

        transfer_service.delete(mock_transfer.id)

        mock_transfer_repo.delete.assert_called_once_with(mock_transfer)

    def test_delete_not_found(self, transfer_service, mock_transfer_repo):
        """Should raise NotFoundError and never call delete when transfer is absent."""
        mock_transfer_repo.get_by_id_or_fail.side_effect = NotFoundError(
            "Transfer", str(uuid4())
        )

        with pytest.raises(NotFoundError):
            transfer_service.delete(uuid4())

        mock_transfer_repo.delete.assert_not_called()
