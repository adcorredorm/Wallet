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
        cuenta_id: UUID | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Transfer], int]:
        """
        Get transfers with filters and pagination.

        Args:
            cuenta_id: Filter by account (source or destination)
            fecha_desde: Filter by start date
            fecha_hasta: Filter by end date
            tags: Filter by tags
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (list of transfers, total count)
        """
        offset = (page - 1) * limit

        return self.repository.get_filtered(
            cuenta_id=cuenta_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def create(
        self,
        cuenta_origen_id: UUID,
        cuenta_destino_id: UUID,
        monto: Decimal,
        fecha: date,
        descripcion: str | None = None,
        tags: list[str] | None = None,
        client_id: str | None = None,
    ) -> Transfer:
        """
        Create a new transfer.

        If client_id is provided and a record with that key already exists in
        the database the existing transfer is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        Args:
            cuenta_origen_id: Source account ID
            cuenta_destino_id: Destination account ID
            monto: Transfer amount
            fecha: Transfer date
            descripcion: Optional description
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
        cuenta_origen = self.account_repository.get_by_id_or_fail(cuenta_origen_id)
        cuenta_destino = self.account_repository.get_by_id_or_fail(cuenta_destino_id)

        # Validate same currency
        if cuenta_origen.divisa != cuenta_destino.divisa:
            raise BusinessRuleError(
                f"No se pueden transferir fondos entre cuentas con diferentes divisas. "
                f"Cuenta origen: {cuenta_origen.divisa}, Cuenta destino: {cuenta_destino.divisa}"
            )

        return self.repository.create(
            cuenta_origen_id=cuenta_origen_id,
            cuenta_destino_id=cuenta_destino_id,
            monto=monto,
            fecha=fecha,
            descripcion=descripcion,
            tags=tags or [],
            client_id=client_id,
        )

    def update(
        self,
        transfer_id: UUID,
        monto: Decimal | None = None,
        fecha: date | None = None,
        descripcion: str | None = None,
        tags: list[str] | None = None,
    ) -> Transfer:
        """
        Update an existing transfer.

        Note: Cannot change source or destination accounts.

        Args:
            transfer_id: Transfer UUID
            monto: New amount
            fecha: New date
            descripcion: New description
            tags: New tags

        Returns:
            Updated transfer instance

        Raises:
            NotFoundError: If transfer not found
        """
        transfer = self.repository.get_by_id_or_fail(transfer_id)

        update_data = {}
        if monto is not None:
            update_data["monto"] = monto
        if fecha is not None:
            update_data["fecha"] = fecha
        if descripcion is not None:
            update_data["descripcion"] = descripcion
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
