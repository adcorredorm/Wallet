"""
Account model representing financial accounts.

Accounts can be debit, credit, or cash accounts and support multiple currencies.
Balance is calculated dynamically from transactions and transfers.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, String, Boolean, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer


class AccountType(enum.Enum):
    """Enumeration of supported account types."""

    DEBIT = "debit"
    CREDIT = "credit"
    CASH = "cash"


class Account(BaseModel):
    """
    Financial account model.

    Attributes:
        name: Account name (max 100 characters)
        type: Account type (debit, credit, cash)
        currency: Currency code (ISO 4217, 3 characters)
        description: Optional account description
        tags: List of tags for categorization
        active: Whether the account is active (soft delete)
        transactions: Related transactions
        transfers_source: Transfers where this is the source account
        transfers_destination: Transfers where this is the destination account
    """

    __tablename__ = "accounts"

    name = Column(String(100), nullable=False)
    type = Column(Enum(AccountType), nullable=False)
    currency = Column(String(3), nullable=False)  # ISO 4217
    description = Column(String(500), nullable=True)
    tags = Column(ARRAY(String(50)), default=list, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    # Relationships
    transactions = relationship(
        "Transaction",
        back_populates="account",
        lazy="dynamic",
    )
    transfers_source = relationship(
        "Transfer",
        foreign_keys="Transfer.source_account_id",
        back_populates="source_account",
        lazy="dynamic",
    )
    transfers_destination = relationship(
        "Transfer",
        foreign_keys="Transfer.destination_account_id",
        back_populates="destination_account",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "offline_id", name="uq_accounts_user_offline"),
    )

    def __repr__(self) -> str:
        """String representation of the account."""
        return f"<Account {self.name} ({self.currency})>"
