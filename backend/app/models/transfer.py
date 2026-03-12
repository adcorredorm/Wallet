"""
Transfer model for money movements between accounts.

Transfers represent money moving from one account to another. Both accounts
must use the same currency.
"""

from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import Column, String, ForeignKey, Date, Numeric, Index
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
        amount: Transfer amount (positive decimal with 2 decimal places)
        date: Transfer date
        description: Optional transfer description
        tags: List of tags for categorization
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

    # Indexes for performance
    __table_args__ = (
        Index("idx_transfers_source", "source_account_id"),
        Index("idx_transfers_destination", "destination_account_id"),
        Index("idx_transfers_date", "date"),
    )

    def __repr__(self) -> str:
        """String representation of the transfer."""
        return f"<Transfer {self.amount} on {self.date}>"
