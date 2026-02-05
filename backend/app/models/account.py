"""
Account model representing financial accounts.

Accounts can be debit, credit, or cash accounts and support multiple currencies.
Balance is calculated dynamically from transactions and transfers.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer


class AccountType(enum.Enum):
    """Enumeration of supported account types."""

    DEBITO = "debito"
    CREDITO = "credito"
    EFECTIVO = "efectivo"


class Account(BaseModel):
    """
    Financial account model.

    Attributes:
        nombre: Account name (max 100 characters)
        tipo: Account type (debit, credit, cash)
        divisa: Currency code (ISO 4217, 3 characters)
        descripcion: Optional account description
        tags: List of tags for categorization
        activa: Whether the account is active (soft delete)
        transacciones: Related transactions
        transferencias_origen: Transfers where this is the source account
        transferencias_destino: Transfers where this is the destination account
    """

    __tablename__ = "cuentas"

    nombre = Column(String(100), nullable=False)
    tipo = Column(Enum(AccountType), nullable=False)
    divisa = Column(String(3), nullable=False)  # ISO 4217
    descripcion = Column(String(500), nullable=True)
    tags = Column(ARRAY(String(50)), default=list, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)

    # Relationships
    transacciones = relationship(
        "Transaction",
        back_populates="cuenta",
        lazy="dynamic",
    )
    transferencias_origen = relationship(
        "Transfer",
        foreign_keys="Transfer.cuenta_origen_id",
        back_populates="cuenta_origen",
        lazy="dynamic",
    )
    transferencias_destino = relationship(
        "Transfer",
        foreign_keys="Transfer.cuenta_destino_id",
        back_populates="cuenta_destino",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        """String representation of the account."""
        return f"<Account {self.nombre} ({self.divisa})>"
