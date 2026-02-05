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

    INGRESO = "ingreso"
    GASTO = "gasto"


class Transaction(BaseModel):
    """
    Transaction model for income and expense records.

    Attributes:
        tipo: Transaction type (income or expense)
        monto: Transaction amount (positive decimal with 2 decimal places)
        fecha: Transaction date
        cuenta_id: Associated account ID
        categoria_id: Associated category ID
        titulo: Optional transaction title
        descripcion: Optional transaction description
        tags: List of tags for categorization
        cuenta: Related account
        categoria: Related category
    """

    __tablename__ = "transacciones"

    tipo = Column(Enum(TransactionType), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    cuenta_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cuentas.id"),
        nullable=False,
    )
    categoria_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categorias.id"),
        nullable=False,
    )
    titulo = Column(String(100), nullable=True)
    descripcion = Column(String(500), nullable=True)
    tags = Column(ARRAY(String(50)), default=list, nullable=False)

    # Relationships
    cuenta = relationship(
        "Account",
        back_populates="transacciones",
    )
    categoria = relationship(
        "Category",
        back_populates="transacciones",
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_transacciones_cuenta_fecha", "cuenta_id", "fecha"),
        Index("idx_transacciones_cuenta_tipo", "cuenta_id", "tipo"),
        Index("idx_transacciones_categoria", "categoria_id"),
        Index("idx_transacciones_fecha", "fecha"),
    )

    def __repr__(self) -> str:
        """String representation of the transaction."""
        return f"<Transaction {self.tipo.value} {self.monto} on {self.fecha}>"
