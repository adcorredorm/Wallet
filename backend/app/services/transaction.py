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
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Transaction], int]:
        """
        Get transactions with filters and pagination.

        Args:
            account_id: Filter by account
            category_id: Filter by category
            type: Filter by transaction type
            date_from: Filter by start date
            date_to: Filter by end date
            tags: Filter by tags
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (list of transactions, total count)
        """
        type_enum = TransactionType(type) if type else None
        offset = (page - 1) * limit

        return self.repository.get_filtered(
            account_id=account_id,
            category_id=category_id,
            type=type_enum,
            date_from=date_from,
            date_to=date_to,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def create(
        self,
        type: str,
        amount: Decimal,
        date: date,
        account_id: UUID,
        category_id: UUID,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        client_id: str | None = None,
    ) -> Transaction:
        """
        Create a new transaction.

        If client_id is provided and a record with that key already exists in
        the database the existing transaction is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        Args:
            type: Transaction type (income or expense)
            amount: Transaction amount
            date: Transaction date
            account_id: Account ID
            category_id: Category ID
            title: Optional title
            description: Optional description
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
        account = self.account_repository.get_by_id_or_fail(account_id)

        # Validate category exists
        category = self.category_repository.get_by_id_or_fail(category_id)

        # Validate category type compatibility
        type_enum = TransactionType(type)
        self._validate_category_type(type_enum, category.type)

        return self.repository.create(
            type=type_enum,
            amount=amount,
            date=date,
            account_id=account_id,
            category_id=category_id,
            title=title,
            description=description,
            tags=tags or [],
            client_id=client_id,
        )

    def update(
        self,
        transaction_id: UUID,
        type: str | None = None,
        amount: Decimal | None = None,
        date: date | None = None,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> Transaction:
        """
        Update an existing transaction.

        Args:
            transaction_id: Transaction UUID
            type: New transaction type
            amount: New amount
            date: New date
            account_id: New account ID
            category_id: New category ID
            title: New title
            description: New description
            tags: New tags

        Returns:
            Updated transaction instance

        Raises:
            NotFoundError: If transaction, account, or category not found
            BusinessRuleError: If new category type is incompatible
        """
        transaction = self.repository.get_by_id_or_fail(transaction_id)

        # Validate account if changing
        if account_id:
            self.account_repository.get_by_id_or_fail(account_id)

        # Validate category and type compatibility if changing
        if category_id or type:
            effective_type = TransactionType(type) if type else transaction.type
            effective_category_id = category_id if category_id else transaction.category_id

            category = self.category_repository.get_by_id_or_fail(effective_category_id)
            self._validate_category_type(effective_type, category.type)

        update_data = {}
        if type is not None:
            update_data["type"] = TransactionType(type)
        if amount is not None:
            update_data["amount"] = amount
        if date is not None:
            update_data["date"] = date
        if account_id is not None:
            update_data["account_id"] = account_id
        if category_id is not None:
            update_data["category_id"] = category_id
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
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
            transaction_type: Transaction type (INCOME or EXPENSE)
            category_type: Category type (INCOME, EXPENSE, or BOTH)

        Raises:
            BusinessRuleError: If types are incompatible
        """
        if category_type == CategoryType.BOTH:
            return  # BOTH is compatible with both transaction types

        # Map transaction type to category type
        expected_category_type = (
            CategoryType.INCOME
            if transaction_type == TransactionType.INCOME
            else CategoryType.EXPENSE
        )

        if category_type != expected_category_type:
            raise BusinessRuleError(
                f"La categoria de tipo '{category_type.value}' no es compatible "
                f"con transacciones de tipo '{transaction_type.value}'"
            )
