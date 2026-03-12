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
        original_amount: Decimal | None = None,
        original_currency: str | None = None,
        exchange_rate: Decimal | None = None,
        base_rate: Decimal | None = None,
    ) -> Transaction:
        """
        Create a new transaction.

        If client_id is provided and a record with that key already exists in
        the database the existing transaction is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        When original_currency equals the account's native currency the three
        multi-currency fields are cleared — they would be redundant metadata.

        ``amount`` (in the account's native currency) is always the
        authoritative value stored for balance calculations.  The three
        original_* fields are display-only metadata and never affect balance
        computation.

        Args:
            type: Transaction type (income or expense)
            amount: Transaction amount in the account's native currency
            date: Transaction date
            account_id: Account ID
            category_id: Category ID
            title: Optional title
            description: Optional description
            tags: Optional tags
            client_id: Optional client-generated idempotency key
            original_amount: Amount in the foreign currency before conversion.
                Must be > 0 when provided.
            original_currency: ISO 4217 code of the foreign currency.
            exchange_rate: Units of account currency per 1 unit of
                original_currency at transaction time. Must be > 0 when
                provided.
            base_rate: Units of primaryCurrency per 1 unit of the account's
                native currency at transaction time. Stored as-is; NULL when
                unavailable offline.

        Returns:
            Created or pre-existing transaction instance

        Raises:
            NotFoundError: If account or category not found
            BusinessRuleError: If category type is incompatible with
                transaction type
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

        # Resolve multi-currency metadata.
        # If the original currency matches the account's own currency the three
        # fields are redundant — clear them so we never store useless data.
        if original_currency is not None and original_currency == account.currency:
            original_amount = None
            original_currency = None
            exchange_rate = None

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
            original_amount=original_amount,
            original_currency=original_currency,
            exchange_rate=exchange_rate,
            base_rate=base_rate,
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
        original_amount: Decimal | None = None,
        original_currency: str | None = None,
        exchange_rate: Decimal | None = None,
        base_rate: Decimal | None = None,
    ) -> Transaction:
        """
        Update an existing transaction.

        Multi-currency fields follow the same consistency rules as create: if
        any of the three are present in the payload they must form a complete
        and valid set (original_currency present, original_amount > 0,
        exchange_rate > 0).  Passing only a subset raises BusinessRuleError.

        Args:
            transaction_id: Transaction UUID
            type: New transaction type
            amount: New amount in the account's native currency
            date: New date
            account_id: New account ID
            category_id: New category ID
            title: New title
            description: New description
            tags: New tags
            original_amount: New original amount in the foreign currency.
            original_currency: New ISO 4217 foreign currency code.
            exchange_rate: New exchange rate (account currency per foreign unit).
            base_rate: Units of primaryCurrency per 1 unit of the account's
                native currency at transaction time. Stored as-is; NULL when
                unavailable offline.

        Returns:
            Updated transaction instance

        Raises:
            NotFoundError: If transaction, account, or category not found
            BusinessRuleError: If new category type is incompatible or if the
                multi-currency fields are inconsistently provided
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

        # Validate multi-currency field consistency when any of the three are
        # present in the update payload.
        has_currency = original_currency is not None
        has_amount = original_amount is not None
        has_rate = exchange_rate is not None

        if has_currency or has_amount or has_rate:
            if not has_currency:
                raise BusinessRuleError(
                    "original_currency es requerido cuando original_amount o exchange_rate son proporcionados"
                )
            if not has_amount:
                raise BusinessRuleError(
                    "original_amount es requerido cuando original_currency es proporcionado"
                )
            if not has_rate:
                raise BusinessRuleError(
                    "exchange_rate es requerido cuando original_currency es proporcionado"
                )
            if original_amount <= 0:
                raise BusinessRuleError("original_amount debe ser mayor a 0")
            if exchange_rate <= 0:
                raise BusinessRuleError("exchange_rate debe ser mayor a 0")

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
        if original_amount is not None:
            update_data["original_amount"] = original_amount
        if original_currency is not None:
            update_data["original_currency"] = original_currency
        if exchange_rate is not None:
            update_data["exchange_rate"] = exchange_rate
        if base_rate is not None:
            update_data["base_rate"] = base_rate

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
