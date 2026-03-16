"""
Account service containing business logic for account operations.

Every public method accepts a user_id parameter and passes it to the
repository so queries are always scoped to a single user.
"""

from datetime import datetime
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, func

from app.extensions import db
from app.models import Account
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.repositories import AccountRepository
from app.utils.exceptions import NotFoundError, BusinessRuleError


class AccountService:
    """Service for account business logic."""

    def __init__(self):
        """Initialize account service with repository."""
        self.repository = AccountRepository()

    def get_all(
        self, user_id: UUID, include_archived: bool = False
    ) -> list[Account]:
        """
        Get all accounts for a user, optionally including archived ones.

        Args:
            user_id: Owner's UUID.
            include_archived: Whether to include inactive accounts.

        Returns:
            List of accounts.
        """
        if include_archived:
            return self.repository.get_all(user_id=user_id, include_archived=True)
        return self.repository.get_all_active(user_id=user_id)

    def get_by_id(self, account_id: UUID, user_id: UUID) -> Account:
        """
        Get an account by ID, scoped to the owner.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.

        Returns:
            Account instance.

        Raises:
            NotFoundError: If account not found or not owned by this user.
        """
        return self.repository.get_by_id_or_fail(account_id, user_id)

    def get_with_balance(
        self, account_id: UUID, user_id: UUID
    ) -> tuple[Account, Decimal]:
        """
        Get an account with its calculated balance.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.

        Returns:
            Tuple of (account instance, balance).

        Raises:
            NotFoundError: If account not found or not owned by this user.
        """
        account = self.repository.get_by_id_or_fail(account_id, user_id)
        balance = self.repository.calculate_balance(account_id, user_id)
        return account, balance

    def get_all_with_balances(
        self, user_id: UUID, include_archived: bool = False
    ) -> list[tuple[Account, Decimal]]:
        """
        Get all accounts with their calculated balances.

        Args:
            user_id: Owner's UUID.
            include_archived: Whether to include inactive accounts.

        Returns:
            List of tuples (account, balance).
        """
        accounts = self.get_all(user_id=user_id, include_archived=include_archived)
        # N+1: issues 4 queries per account (income, expenses, transfers_in, transfers_out).
        # Acceptable for personal use with few accounts. Optimize with a single aggregated
        # query if performance becomes an issue.
        return [
            (account, self.repository.calculate_balance(account.id, user_id))
            for account in accounts
        ]

    def get_all_with_balances_since(
        self, user_id: UUID, updated_since: datetime
    ) -> list[tuple[Account, Decimal]]:
        """
        Return accounts modified since updated_since with balances.

        Always includes archived accounts (to propagate active=False changes).
        Used by incremental sync.

        Args:
            user_id: Owner's UUID.
            updated_since: Cutoff timestamp (naive UTC, inclusive). Only accounts
                with updated_at >= updated_since are returned.

        Returns:
            List of tuples (account, balance) for accounts modified since the cutoff.
        """
        accounts = self.repository.get_all(
            user_id=user_id,
            updated_since=updated_since,
            include_archived=True,
        )
        # N+1: issues 4 queries per account (income, expenses, transfers_in, transfers_out).
        # Acceptable for personal use with few accounts. Optimize with a single aggregated
        # query if performance becomes an issue.
        return [
            (account, self.repository.calculate_balance(account.id, user_id))
            for account in accounts
        ]

    def create(
        self,
        user_id: UUID,
        name: str,
        type: str,
        currency: str,
        description: str | None = None,
        tags: list[str] | None = None,
        client_id: str | None = None,
    ) -> Account:
        """
        Create a new account for a user.

        If client_id is provided and a record with that key already exists in
        the database the existing account is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        Args:
            user_id: Owner's UUID.
            name: Account name.
            type: Account type.
            currency: Currency code (ISO 4217).
            description: Optional description.
            tags: Optional list of tags.
            client_id: Optional client-generated idempotency key.

        Returns:
            Created or pre-existing account instance.
        """
        from app.models.account import AccountType

        if client_id:
            existing = self.repository.get_by_client_id(client_id, user_id)
            if existing:
                return existing

        return self.repository.create(
            user_id=user_id,
            name=name,
            type=AccountType(type),
            currency=currency.upper(),
            description=description,
            tags=tags or [],
            client_id=client_id,
        )

    def update(
        self,
        account_id: UUID,
        user_id: UUID,
        name: str | None = None,
        type: str | None = None,
        currency: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        active: bool | None = None,
    ) -> Account:
        """
        Update an existing account.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.
            name: New account name.
            type: New account type.
            currency: New currency code.
            description: New description.
            tags: New tags list.
            active: New active status.

        Returns:
            Updated account instance.

        Raises:
            NotFoundError: If account not found or not owned by this user.
        """
        from app.models.account import AccountType

        account = self.repository.get_by_id_or_fail(account_id, user_id)

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if type is not None:
            update_data["type"] = AccountType(type)
        if currency is not None:
            update_data["currency"] = currency.upper()
        if description is not None:
            update_data["description"] = description
        if tags is not None:
            update_data["tags"] = tags
        if active is not None:
            update_data["active"] = active

        return self.repository.update(account, **update_data)

    def archive(self, account_id: UUID, user_id: UUID) -> Account:
        """
        Archive an account (soft delete).

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.

        Returns:
            Archived account instance.

        Raises:
            NotFoundError: If account not found or not owned by this user.
        """
        return self.repository.soft_delete(account_id, user_id)

    def delete(self, account_id: UUID, user_id: UUID) -> None:
        """
        Permanently delete an account.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.

        Raises:
            NotFoundError: If account not found or not owned by this user.
            BusinessRuleError: If account has transactions or transfers.
        """
        account = self.repository.get_by_id_or_fail(account_id, user_id)

        txn_count = db.session.execute(
            select(func.count()).select_from(Transaction).where(
                Transaction.account_id == account.id
            )
        ).scalar()
        if txn_count > 0:
            raise BusinessRuleError(
                "No se puede eliminar una cuenta con transacciones. "
                "Use archivar en su lugar."
            )

        transfer_count = db.session.execute(
            select(func.count()).select_from(Transfer).where(
                (Transfer.source_account_id == account.id)
                | (Transfer.destination_account_id == account.id)
            )
        ).scalar()
        if transfer_count > 0:
            raise BusinessRuleError(
                "No se puede eliminar una cuenta con transferencias. "
                "Use archivar en su lugar."
            )

        self.repository.delete(account)

    def get_balance(self, account_id: UUID, user_id: UUID) -> Decimal:
        """
        Get calculated balance for an account.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.

        Returns:
            Account balance.

        Raises:
            NotFoundError: If account not found or not owned by this user.
        """
        self.repository.get_by_id_or_fail(account_id, user_id)
        return self.repository.calculate_balance(account_id, user_id)
