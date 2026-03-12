"""
Account repository for database operations.
"""

from typing import Optional
from uuid import UUID
from decimal import Decimal

from sqlalchemy import func, case
from app.extensions import db
from app.models import Account, Transaction, Transfer, TransactionType
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Repository for Account entity operations."""

    def __init__(self):
        """Initialize account repository."""
        super().__init__(Account)

    def get_all_active(self) -> list[Account]:
        """
        Get all active accounts.

        Returns:
            List of active accounts
        """
        return (
            db.session.execute(db.select(Account).where(Account.active == True))
            .scalars()
            .all()
        )

    def get_by_currency(self, currency: str) -> list[Account]:
        """
        Get all accounts with a specific currency.

        Args:
            currency: Currency code (ISO 4217)

        Returns:
            List of accounts with the specified currency
        """
        return (
            db.session.execute(
                db.select(Account).where(Account.currency == currency.upper())
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
            account_id: Account UUID

        Returns:
            Calculated balance as Decimal
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

        # Sum of incoming transfers
        transfers_in = (
            db.session.query(func.coalesce(func.sum(Transfer.amount), 0))
            .filter(Transfer.destination_account_id == account_id)
            .scalar()
        )

        # Sum of outgoing transfers
        transfers_out = (
            db.session.query(func.coalesce(func.sum(Transfer.amount), 0))
            .filter(Transfer.source_account_id == account_id)
            .scalar()
        )

        balance = Decimal(str(income)) - Decimal(str(expenses)) + Decimal(str(transfers_in)) - Decimal(str(transfers_out))
        return balance

    def soft_delete(self, account_id: UUID) -> Account:
        """
        Soft delete an account by setting active to False.

        Args:
            account_id: Account UUID

        Returns:
            Updated account instance
        """
        account = self.get_by_id_or_fail(account_id)
        account.active = False
        db.session.commit()
        db.session.refresh(account)
        return account
