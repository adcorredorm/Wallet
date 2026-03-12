"""
Transfer service containing business logic for transfer operations.
"""

from uuid import UUID
from datetime import date
from decimal import Decimal

from app.models import Transfer
from app.repositories import TransferRepository, AccountRepository
from app.utils.exceptions import NotFoundError, BusinessRuleError, ValidationError


class TransferService:
    """Service for transfer business logic."""

    def __init__(self):
        """Initialize transfer service with repositories."""
        self.repository = TransferRepository()
        self.account_repository = AccountRepository()

    def get_by_id(self, transfer_id: UUID) -> Transfer:
        """
        Get a transfer by ID with related data.

        Args:
            transfer_id: Transfer UUID

        Returns:
            Transfer instance with accounts loaded

        Raises:
            NotFoundError: If transfer not found
        """
        transfer = self.repository.get_with_relations(transfer_id)
        if not transfer:
            raise NotFoundError("Transfer", str(transfer_id))
        return transfer

    def get_filtered(
        self,
        account_id: UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Transfer], int]:
        """
        Get transfers with filters and pagination.

        Args:
            account_id: Filter by account (source or destination)
            date_from: Filter by start date
            date_to: Filter by end date
            tags: Filter by tags
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (list of transfers, total count)
        """
        offset = (page - 1) * limit

        return self.repository.get_filtered(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def create(
        self,
        source_account_id: UUID,
        destination_account_id: UUID,
        amount: Decimal,
        date: date,
        description: str | None = None,
        tags: list[str] | None = None,
        client_id: str | None = None,
        destination_amount: Decimal | None = None,
        exchange_rate: Decimal | None = None,
        destination_currency: str | None = None,
    ) -> Transfer:
        """
        Create a new transfer, handling both same-currency and cross-currency cases.

        If client_id is provided and a record with that key already exists in
        the database the existing transfer is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        For same-currency transfers, destination_amount is set equal to amount,
        exchange_rate is set to 1, and destination_currency is left NULL.

        For cross-currency transfers, destination_amount and exchange_rate must
        be supplied by the caller. destination_currency is auto-derived from the
        destination account's currency field.

        Args:
            source_account_id: Source account ID
            destination_account_id: Destination account ID
            amount: Transfer amount in source currency (positive)
            date: Transfer date
            description: Optional description
            tags: Optional tags
            client_id: Optional client-generated idempotency key
            destination_amount: Amount credited to destination account in its
                currency. Required for cross-currency transfers.
            exchange_rate: Exchange rate at transfer time. Required for
                cross-currency transfers.
            destination_currency: Ignored — always derived from the destination
                account. Accepted for symmetry with the schema but not used.

        Returns:
            Created or pre-existing transfer instance

        Raises:
            NotFoundError: If source or destination account not found
            ValidationError: If cross-currency transfer is missing
                destination_amount or exchange_rate
        """
        if client_id:
            existing = self.repository.get_by_client_id(client_id)
            if existing:
                return existing

        # Validate both accounts exist
        source_account = self.account_repository.get_by_id_or_fail(source_account_id)
        destination_account = self.account_repository.get_by_id_or_fail(destination_account_id)

        cross_currency = source_account.currency != destination_account.currency

        if cross_currency:
            # Both fields are mandatory for cross-currency transfers
            if destination_amount is None or exchange_rate is None:
                raise ValidationError(
                    "destination_amount and exchange_rate are required for cross-currency transfers"
                )
            resolved_destination_currency = destination_account.currency
        else:
            # Same-currency: normalise to canonical values so balance queries
            # can always use COALESCE(destination_amount, amount) safely.
            destination_amount = amount
            exchange_rate = Decimal("1")
            resolved_destination_currency = None

        return self.repository.create(
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount=amount,
            date=date,
            description=description,
            tags=tags or [],
            client_id=client_id,
            destination_amount=destination_amount,
            exchange_rate=exchange_rate,
            destination_currency=resolved_destination_currency,
        )

    def update(
        self,
        transfer_id: UUID,
        amount: Decimal | None = None,
        date: date | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        destination_amount: Decimal | None = None,
        exchange_rate: Decimal | None = None,
    ) -> Transfer:
        """
        Update an existing transfer.

        Source and destination accounts cannot be changed through an update.
        Therefore the same-currency vs. cross-currency nature of the transfer
        is fixed at creation time and cannot be altered here.

        Args:
            transfer_id: Transfer UUID
            amount: New amount in source currency
            date: New date
            description: New description
            tags: New tags
            destination_amount: New destination amount. When provided must be > 0.
                Only meaningful for cross-currency transfers.
            exchange_rate: New exchange rate. When provided must be > 0.
                Only meaningful for cross-currency transfers.

        Returns:
            Updated transfer instance

        Raises:
            NotFoundError: If transfer not found
            ValidationError: If destination_amount or exchange_rate are <= 0
        """
        transfer = self.repository.get_by_id_or_fail(transfer_id)

        if destination_amount is not None and destination_amount <= 0:
            raise ValidationError("destination_amount debe ser mayor a 0")
        if exchange_rate is not None and exchange_rate <= 0:
            raise ValidationError("exchange_rate debe ser mayor a 0")

        update_data: dict = {}
        if amount is not None:
            update_data["amount"] = amount
        if date is not None:
            update_data["date"] = date
        if description is not None:
            update_data["description"] = description
        if tags is not None:
            update_data["tags"] = tags
        if destination_amount is not None:
            update_data["destination_amount"] = destination_amount
        if exchange_rate is not None:
            update_data["exchange_rate"] = exchange_rate

        return self.repository.update(transfer, **update_data)

    def delete(self, transfer_id: UUID) -> None:
        """
        Delete a transfer.

        Args:
            transfer_id: Transfer UUID

        Raises:
            NotFoundError: If transfer not found
        """
        transfer = self.repository.get_by_id_or_fail(transfer_id)
        self.repository.delete(transfer)
