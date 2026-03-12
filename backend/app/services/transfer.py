"""
Transfer service containing business logic for transfer operations.
"""

from uuid import UUID
from datetime import date
from decimal import Decimal

from app.models import Transfer
from app.repositories import TransferRepository, AccountRepository
from app.utils.exceptions import NotFoundError, BusinessRuleError


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
    ) -> Transfer:
        """
        Create a new transfer.

        If client_id is provided and a record with that key already exists in
        the database the existing transfer is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        Args:
            source_account_id: Source account ID
            destination_account_id: Destination account ID
            amount: Transfer amount
            date: Transfer date
            description: Optional description
            tags: Optional tags
            client_id: Optional client-generated idempotency key

        Returns:
            Created or pre-existing transfer instance

        Raises:
            NotFoundError: If source or destination account not found
            BusinessRuleError: If accounts have different currencies
        """
        if client_id:
            existing = self.repository.get_by_client_id(client_id)
            if existing:
                return existing

        # Validate both accounts exist
        source_account = self.account_repository.get_by_id_or_fail(source_account_id)
        destination_account = self.account_repository.get_by_id_or_fail(destination_account_id)

        # Validate same currency
        if source_account.currency != destination_account.currency:
            raise BusinessRuleError(
                f"No se pueden transferir fondos entre cuentas con diferentes divisas. "
                f"Cuenta origen: {source_account.currency}, Cuenta destino: {destination_account.currency}"
            )

        return self.repository.create(
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount=amount,
            date=date,
            description=description,
            tags=tags or [],
            client_id=client_id,
        )

    def update(
        self,
        transfer_id: UUID,
        amount: Decimal | None = None,
        date: date | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Transfer:
        """
        Update an existing transfer.

        Note: Cannot change source or destination accounts.

        Args:
            transfer_id: Transfer UUID
            amount: New amount
            date: New date
            description: New description
            tags: New tags

        Returns:
            Updated transfer instance

        Raises:
            NotFoundError: If transfer not found
        """
        transfer = self.repository.get_by_id_or_fail(transfer_id)

        update_data = {}
        if amount is not None:
            update_data["amount"] = amount
        if date is not None:
            update_data["date"] = date
        if description is not None:
            update_data["description"] = description
        if tags is not None:
            update_data["tags"] = tags

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
