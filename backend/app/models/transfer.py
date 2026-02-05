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
        cuenta_origen_id: Source account ID
        cuenta_destino_id: Destination account ID
        monto: Transfer amount (positive decimal with 2 decimal places)
        fecha: Transfer date
        descripcion: Optional transfer description
        tags: List of tags for categorization
        cuenta_origen: Source account relationship
        cuenta_destino: Destination account relationship
    """

    __tablename__ = "transferencias"

    cuenta_origen_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cuentas.id"),
        nullable=False,
    )
    cuenta_destino_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cuentas.id"),
        nullable=False,
    )
    monto = Column(Numeric(15, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    descripcion = Column(String(500), nullable=True)
    tags = Column(ARRAY(String(50)), default=list, nullable=False)

    # Relationships
    cuenta_origen = relationship(
        "Account",
        foreign_keys=[cuenta_origen_id],
        back_populates="transferencias_origen",
    )
    cuenta_destino = relationship(
        "Account",
        foreign_keys=[cuenta_destino_id],
        back_populates="transferencias_destino",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_transferencias_origen", "cuenta_origen_id"),
        Index("idx_transferencias_destino", "cuenta_destino_id"),
        Index("idx_transferencias_fecha", "fecha"),
    )

    def __repr__(self) -> str:
        """String representation of the transfer."""
        return f"<Transfer {self.monto} on {self.fecha}>"
