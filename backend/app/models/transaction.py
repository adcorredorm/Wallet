"""
Transaction model for income and expense records.

Transactions represent money flowing in or out of an account and must be
associated with both an account and a category.
"""

import enum
from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import Column, String, Enum, ForeignKey, Date, Numeric, Index
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class TransactionType(enum.Enum):
    """Enumeration of transaction types."""

    INCOME = "income"
    EXPENSE = "expense"


class Transaction(BaseModel):
    """
    Transaction model for income and expense records.

    Attributes:
        type: Transaction type (income or expense)
        amount: Transaction amount (positive decimal, stored in account's currency)
        date: Transaction date
        account_id: Associated account ID
        category_id: Associated category ID
        title: Optional transaction title
        description: Optional transaction description
        tags: List of tags for categorization
        original_amount: Amount in the original transaction currency (NULL for
            single-currency transactions)
        original_currency: ISO 4217 code of the original transaction currency
            (NULL for single-currency transactions)
        exchange_rate: Rate applied at transaction time, original currency /
            account currency (NULL for single-currency transactions)
        base_rate: Units of primaryCurrency per 1 unit of the account's native
            currency, snapshotted at transaction time. NULL when the rate was
            unavailable offline.
        account: Related account
        category: Related category
    """

    __tablename__ = "transactions"

    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    date = Column(Date, nullable=False)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=False,
    )
    title = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    tags = Column(ARRAY(String(50)), default=list, nullable=False)
    original_amount = Column(Numeric(20, 8), nullable=True)
    original_currency = Column(String(10), nullable=True)
    exchange_rate = Column(Numeric(20, 10), nullable=True)
    base_rate = Column(Numeric(20, 10), nullable=True)

    # Relationships
    account = relationship(
        "Account",
        back_populates="transactions",
    )
    category = relationship(
        "Category",
        back_populates="transactions",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_transactions_account_date", "account_id", "date"),
        Index("idx_transactions_account_type", "account_id", "type"),
        Index("idx_transactions_category", "category_id"),
        Index("idx_transactions_date", "date"),
    )

    def __repr__(self) -> str:
        """String representation of the transaction."""
        return f"<Transaction {self.type.value} {self.amount} on {self.date}>"
