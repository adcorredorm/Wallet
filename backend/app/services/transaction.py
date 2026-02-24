"""
Transaction service containing business logic for transaction operations.
"""

from uuid import UUID
from datetime import date
from decimal import Decimal

from app.models import Transaction, TransactionType, CategoryType
from app.repositories import TransactionRepository, AccountRepository, CategoryRepository
from app.utils.exceptions import NotFoundError, BusinessRuleError


class TransactionService:
    """Service for transaction business logic."""

    def __init__(self):
        """Initialize transaction service with repositories."""
        self.repository = TransactionRepository()
        self.account_repository = AccountRepository()
        self.category_repository = CategoryRepository()

    def get_by_id(self, transaction_id: UUID) -> Transaction:
        """
        Get a transaction by ID with related data.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Transaction instance with account and category loaded

        Raises:
            NotFoundError: If transaction not found
        """
        transaction = self.repository.get_with_relations(transaction_id)
        if not transaction:
            raise NotFoundError("Transaction", str(transaction_id))
        return transaction

    def get_filtered(
        self,
        cuenta_id: UUID | None = None,
        categoria_id: UUID | None = None,
        tipo: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Transaction], int]:
        """
        Get transactions with filters and pagination.

        Args:
            cuenta_id: Filter by account
            categoria_id: Filter by category
            tipo: Filter by transaction type
            fecha_desde: Filter by start date
            fecha_hasta: Filter by end date
            tags: Filter by tags
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (list of transactions, total count)
        """
        tipo_enum = TransactionType(tipo) if tipo else None
        offset = (page - 1) * limit

        return self.repository.get_filtered(
            cuenta_id=cuenta_id,
            categoria_id=categoria_id,
            tipo=tipo_enum,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def create(
        self,
        tipo: str,
        monto: Decimal,
        fecha: date,
        cuenta_id: UUID,
        categoria_id: UUID,
        titulo: str | None = None,
        descripcion: str | None = None,
        tags: list[str] | None = None,
        client_id: str | None = None,
    ) -> Transaction:
        """
        Create a new transaction.

        If client_id is provided and a record with that key already exists in
        the database the existing transaction is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        Args:
            tipo: Transaction type (ingreso or gasto)
            monto: Transaction amount
            fecha: Transaction date
            cuenta_id: Account ID
            categoria_id: Category ID
            titulo: Optional title
            descripcion: Optional description
            tags: Optional tags
            client_id: Optional client-generated idempotency key

        Returns:
            Created or pre-existing transaction instance

        Raises:
            NotFoundError: If account or category not found
            BusinessRuleError: If category type is incompatible with transaction type
        """
        if client_id:
            existing = self.repository.get_by_client_id(client_id)
            if existing:
                return existing

        # Validate account exists
        account = self.account_repository.get_by_id_or_fail(cuenta_id)

        # Validate category exists
        category = self.category_repository.get_by_id_or_fail(categoria_id)

        # Validate category type compatibility
        tipo_enum = TransactionType(tipo)
        self._validate_category_type(tipo_enum, category.tipo)

        return self.repository.create(
            tipo=tipo_enum,
            monto=monto,
            fecha=fecha,
            cuenta_id=cuenta_id,
            categoria_id=categoria_id,
            titulo=titulo,
            descripcion=descripcion,
            tags=tags or [],
            client_id=client_id,
        )

    def update(
        self,
        transaction_id: UUID,
        tipo: str | None = None,
        monto: Decimal | None = None,
        fecha: date | None = None,
        cuenta_id: UUID | None = None,
        categoria_id: UUID | None = None,
        titulo: str | None = None,
        descripcion: str | None = None,
        tags: list[str] | None = None,
    ) -> Transaction:
        """
        Update an existing transaction.

        Args:
            transaction_id: Transaction UUID
            tipo: New transaction type
            monto: New amount
            fecha: New date
            cuenta_id: New account ID
            categoria_id: New category ID
            titulo: New title
            descripcion: New description
            tags: New tags

        Returns:
            Updated transaction instance

        Raises:
            NotFoundError: If transaction, account, or category not found
            BusinessRuleError: If new category type is incompatible
        """
        transaction = self.repository.get_by_id_or_fail(transaction_id)

        # Validate account if changing
        if cuenta_id:
            self.account_repository.get_by_id_or_fail(cuenta_id)

        # Validate category and type compatibility if changing
        if categoria_id or tipo:
            effective_tipo = TransactionType(tipo) if tipo else transaction.tipo
            effective_categoria_id = categoria_id if categoria_id else transaction.categoria_id

            category = self.category_repository.get_by_id_or_fail(effective_categoria_id)
            self._validate_category_type(effective_tipo, category.tipo)

        update_data = {}
        if tipo is not None:
            update_data["tipo"] = TransactionType(tipo)
        if monto is not None:
            update_data["monto"] = monto
        if fecha is not None:
            update_data["fecha"] = fecha
        if cuenta_id is not None:
            update_data["cuenta_id"] = cuenta_id
        if categoria_id is not None:
            update_data["categoria_id"] = categoria_id
        if titulo is not None:
            update_data["titulo"] = titulo
        if descripcion is not None:
            update_data["descripcion"] = descripcion
        if tags is not None:
            update_data["tags"] = tags

        return self.repository.update(transaction, **update_data)

    def delete(self, transaction_id: UUID) -> None:
        """
        Delete a transaction.

        Args:
            transaction_id: Transaction UUID

        Raises:
            NotFoundError: If transaction not found
        """
        transaction = self.repository.get_by_id_or_fail(transaction_id)
        self.repository.delete(transaction)

    def _validate_category_type(
        self, transaction_type: TransactionType, category_type: CategoryType
    ) -> None:
        """
        Validate that category type is compatible with transaction type.

        Args:
            transaction_type: Transaction type (INGRESO or GASTO)
            category_type: Category type (INGRESO, GASTO, or AMBOS)

        Raises:
            BusinessRuleError: If types are incompatible
        """
        if category_type == CategoryType.AMBOS:
            return  # AMBOS is compatible with both transaction types

        # Map transaction type to category type
        expected_category_type = (
            CategoryType.INGRESO
            if transaction_type == TransactionType.INGRESO
            else CategoryType.GASTO
        )

        if category_type != expected_category_type:
            raise BusinessRuleError(
                f"La categoria de tipo '{category_type.value}' no es compatible "
                f"con transacciones de tipo '{transaction_type.value}'"
            )
