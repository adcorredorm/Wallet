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
            db.session.execute(db.select(Account).where(Account.activa == True))
            .scalars()
            .all()
        )

    def get_by_currency(self, divisa: str) -> list[Account]:
        """
        Get all accounts with a specific currency.

        Args:
            divisa: Currency code (ISO 4217)

        Returns:
            List of accounts with the specified currency
        """
        return (
            db.session.execute(
                db.select(Account).where(Account.divisa == divisa.upper())
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
            db.session.query(func.coalesce(func.sum(Transaction.monto), 0))
            .filter(
                Transaction.cuenta_id == account_id,
                Transaction.tipo == TransactionType.INGRESO,
            )
            .scalar()
        )

        # Sum of expense transactions
        expenses = (
            db.session.query(func.coalesce(func.sum(Transaction.monto), 0))
            .filter(
                Transaction.cuenta_id == account_id,
                Transaction.tipo == TransactionType.GASTO,
            )
            .scalar()
        )

        # Sum of incoming transfers
        transfers_in = (
            db.session.query(func.coalesce(func.sum(Transfer.monto), 0))
            .filter(Transfer.cuenta_destino_id == account_id)
            .scalar()
        )

        # Sum of outgoing transfers
        transfers_out = (
            db.session.query(func.coalesce(func.sum(Transfer.monto), 0))
            .filter(Transfer.cuenta_origen_id == account_id)
            .scalar()
        )

        balance = Decimal(str(income)) - Decimal(str(expenses)) + Decimal(str(transfers_in)) - Decimal(str(transfers_out))
        return balance

    def soft_delete(self, account_id: UUID) -> Account:
        """
        Soft delete an account by setting activa to False.

        Args:
            account_id: Account UUID

        Returns:
            Updated account instance
        """
        account = self.get_by_id_or_fail(account_id)
        account.activa = False
        db.session.commit()
        db.session.refresh(account)
        return account
