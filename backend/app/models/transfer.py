"""
Transfer model for money movements between accounts.

Transfers represent money moving from one account to another. Same-currency
transfers leave destination_amount, exchange_rate, and destination_currency
as NULL. Cross-currency transfers populate all three fields.
"""

from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import Column, String, ForeignKey, Date, Numeric, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.account import Account


class Transfer(BaseModel):
    """
    Transfer model for inter-account money movements.

    Attributes:
        source_account_id: Source account ID
        destination_account_id: Destination account ID
        amount: Transfer amount (positive decimal, source currency)
        date: Transfer date
        description: Optional transfer description
        tags: List of tags for categorization
        destination_amount: Amount credited to the destination account in its
            own currency (NULL for same-currency transfers)
        exchange_rate: Exchange rate applied at transfer time, expressed as units
            of destination currency per 1 unit of source currency
            (e.g., COP→USD: 0.000244; destination_amount = amount * exchange_rate).
            NULL for same-currency transfers.
        destination_currency: ISO 4217 currency code of the destination account
            (NULL for same-currency transfers)
        base_rate: Units of primaryCurrency per 1 unit of the source account's
            native currency, snapshotted at transfer time. NULL when unavailable
            offline.
        source_account: Source account relationship
        destination_account: Destination account relationship
    """

    __tablename__ = "transfers"

    source_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    destination_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    amount = Column(Numeric(15, 2), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String(500), nullable=True)
    tags = Column(ARRAY(String(50)), default=list, nullable=False)
    destination_amount = Column(Numeric(20, 8), nullable=True)
    exchange_rate = Column(Numeric(20, 10), nullable=True)
    destination_currency = Column(String(10), nullable=True)
    base_rate = Column(Numeric(20, 10), nullable=True)

    # Relationships
    source_account = relationship(
        "Account",
        foreign_keys=[source_account_id],
        back_populates="transfers_source",
    )
    destination_account = relationship(
        "Account",
        foreign_keys=[destination_account_id],
        back_populates="transfers_destination",
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_transfers_source", "source_account_id"),
        Index("idx_transfers_destination", "destination_account_id"),
        Index("idx_transfers_date", "date"),
        UniqueConstraint("user_id", "offline_id", name="uq_transfers_user_offline"),
    )

    def __repr__(self) -> str:
        """String representation of the transfer."""
        return f"<Transfer {self.amount} on {self.date}>"
