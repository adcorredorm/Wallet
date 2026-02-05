"""
Category model for organizing transactions.

Categories can be for income, expenses, or both. They support hierarchical
organization through parent-child relationships.
"""

import enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, String, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class CategoryType(enum.Enum):
    """Enumeration of category types."""

    INGRESO = "ingreso"
    GASTO = "gasto"
    AMBOS = "ambos"


class Category(BaseModel):
    """
    Category model for transaction classification.

    Attributes:
        nombre: Category name (max 50 characters)
        tipo: Category type (income, expense, or both)
        icono: Optional icon identifier
        color: Optional color in hex format (#RRGGBB)
        categoria_padre_id: Optional parent category ID for subcategories
        categoria_padre: Parent category relationship
        subcategorias: Child categories relationship
        transacciones: Related transactions
    """

    __tablename__ = "categorias"

    nombre = Column(String(50), nullable=False)
    tipo = Column(Enum(CategoryType), nullable=False)
    icono = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)  # #RRGGBB
    categoria_padre_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categorias.id"),
        nullable=True,
    )

    # Relationships
    categoria_padre = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="subcategorias",
    )
    subcategorias = relationship(
        "Category",
        back_populates="categoria_padre",
        lazy="dynamic",
    )
    transacciones = relationship(
        "Transaction",
        back_populates="categoria",
        lazy="dynamic",
    )

    # Indexes
    __table_args__ = (
        Index("idx_categorias_tipo", "tipo"),
        Index("idx_categorias_padre", "categoria_padre_id"),
    )

    def __repr__(self) -> str:
        """String representation of the category."""
        return f"<Category {self.nombre} ({self.tipo.value})>"
