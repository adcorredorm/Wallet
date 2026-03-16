"""
Account repository for database operations.

All query methods that return user-owned data require a user_id parameter
to enforce per-user data isolation. The calculate_balance method is the
only exception — it filters by account_id (which is already user-scoped
through the account lookup) rather than user_id directly.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy import func
from app.extensions import db
from app.models import Account, Transaction, Transfer, TransactionType
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Repository for Account entity operations."""

    def __init__(self):
        """Initialize account repository."""
        super().__init__(Account)

    def get_all_active(self, user_id: UUID) -> list[Account]:
        """
        Get all active accounts for a specific user.

        Args:
            user_id: Owner's UUID.

        Returns:
            List of active accounts owned by the user.
        """
        return (
            db.session.execute(
                db.select(Account).where(
                    Account.user_id == user_id,
                    Account.active == True,
                )
            )
            .scalars()
            .all()
        )

    def get_by_currency(self, currency: str, user_id: UUID) -> list[Account]:
        """
        Get all accounts with a specific currency for a user.

        Args:
            currency: Currency code (ISO 4217).
            user_id: Owner's UUID.

        Returns:
            List of accounts with the specified currency.
        """
        return (
            db.session.execute(
                db.select(Account).where(
                    Account.user_id == user_id,
                    Account.currency == currency.upper(),
                )
            )
            .scalars()
            .all()
        )

    def calculate_balance(self, account_id: UUID) -> Decimal:
        """
        Calculate account balance from transactions and transfers.

        Balance calculation:
        - Add all income transactions
        - Subtract all expense transactions
        - Add all incoming transfers
        - Subtract all outgoing transfers

        Args:
            account_id: Account UUID.

        Returns:
            Calculated balance as Decimal.
        """
        # Sum of income transactions
        income = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.account_id == account_id,
                Transaction.type == TransactionType.INCOME,
            )
            .scalar()
        )

        # Sum of expense transactions
        expenses = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.account_id == account_id,
                Transaction.type == TransactionType.EXPENSE,
            )
            .scalar()
        )

        # Sum of incoming transfers.
        # For cross-currency transfers the credited amount is destination_amount,
        # not amount. COALESCE falls back to amount for same-currency transfers
        # where destination_amount is NULL (legacy rows) or where amount was
        # stored as destination_amount by the service layer.
        transfers_in = (
            db.session.query(
                func.coalesce(
                    func.sum(
                        func.coalesce(Transfer.destination_amount, Transfer.amount)
                    ),
                    0,
                )
            )
            .filter(Transfer.destination_account_id == account_id)
            .scalar()
        )

        # Sum of outgoing transfers
        transfers_out = (
            db.session.query(func.coalesce(func.sum(Transfer.amount), 0))
            .filter(Transfer.source_account_id == account_id)
            .scalar()
        )

        balance = (
            Decimal(str(income))
            - Decimal(str(expenses))
            + Decimal(str(transfers_in))
            - Decimal(str(transfers_out))
        )
        return balance

    def get_all(
        self,
        user_id: UUID,
        updated_since: datetime | None = None,
        include_archived: bool = False,
    ) -> list[Account]:
        """
        Get all accounts for a user, optionally filtered by modification time
        and archived status.

        Args:
            user_id: Owner's UUID. Only records owned by this user are returned.
            updated_since: If provided, only return accounts with updated_at >=
                value (naive UTC, inclusive). None returns all matching accounts.
            include_archived: When True, include inactive (archived) accounts.
                For incremental sync, pass True to propagate active=False changes.

        Returns:
            List of Account instances.
        """
        query = db.select(Account).where(Account.user_id == user_id)
        if updated_since is not None:
            query = query.where(Account.updated_at >= updated_since)
        if not include_archived:
            query = query.where(Account.active == True)
        return db.session.execute(query).scalars().all()

    def soft_delete(self, account_id: UUID, user_id: UUID) -> Account:
        """
        Soft delete an account by setting active to False.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID. Used to scope the lookup.

        Returns:
            Updated account instance.

        Raises:
            NotFoundError: If account not found or not owned by this user.
        """
        account = self.get_by_id_or_fail(account_id, user_id)
        account.active = False
        db.session.commit()
        db.session.refresh(account)
        return account
