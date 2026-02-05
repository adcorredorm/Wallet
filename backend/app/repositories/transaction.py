"""
Transaction repository for database operations.
"""

from typing import Optional
from uuid import UUID
from datetime import date

from sqlalchemy import and_
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Transaction, TransactionType
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction entity operations."""

    def __init__(self):
        """Initialize transaction repository."""
        super().__init__(Transaction)

    def get_with_relations(self, transaction_id: UUID) -> Optional[Transaction]:
        """
        Get a transaction with account and category eagerly loaded.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Transaction instance with relations or None
        """
        return db.session.execute(
            db.select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(selectinload(Transaction.cuenta))
            .options(selectinload(Transaction.categoria))
        ).scalar_one_or_none()

    def get_by_account(
        self,
        cuenta_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transaction]:
        """
        Get transactions for a specific account.

        Args:
            cuenta_id: Account UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of transactions
        """
        query = (
            db.select(Transaction)
            .where(Transaction.cuenta_id == cuenta_id)
            .order_by(Transaction.fecha.desc())
        )

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return db.session.execute(query).scalars().all()

    def get_by_category(
        self,
        categoria_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transaction]:
        """
        Get transactions for a specific category.

        Args:
            categoria_id: Category UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of transactions
        """
        query = (
            db.select(Transaction)
            .where(Transaction.categoria_id == categoria_id)
            .order_by(Transaction.fecha.desc())
        )

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return db.session.execute(query).scalars().all()

    def get_filtered(
        self,
        cuenta_id: Optional[UUID] = None,
        categoria_id: Optional[UUID] = None,
        tipo: Optional[TransactionType] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        tags: Optional[list[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """
        Get transactions with filters and pagination.

        Args:
            cuenta_id: Filter by account
            categoria_id: Filter by category
            tipo: Filter by transaction type
            fecha_desde: Filter by start date (inclusive)
            fecha_hasta: Filter by end date (inclusive)
            tags: Filter by tags (any match)
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Tuple of (list of transactions, total count)
        """
        # Build filters
        filters = []

        if cuenta_id:
            filters.append(Transaction.cuenta_id == cuenta_id)
        if categoria_id:
            filters.append(Transaction.categoria_id == categoria_id)
        if tipo:
            filters.append(Transaction.tipo == tipo)
        if fecha_desde:
            filters.append(Transaction.fecha >= fecha_desde)
        if fecha_hasta:
            filters.append(Transaction.fecha <= fecha_hasta)
        if tags:
            # PostgreSQL array overlap operator
            filters.append(Transaction.tags.overlap(tags))

        # Count total matching records
        count_query = db.select(db.func.count()).select_from(Transaction)
        if filters:
            count_query = count_query.where(and_(*filters))
        total = db.session.execute(count_query).scalar()

        # Get paginated results
        query = (
            db.select(Transaction)
            .options(selectinload(Transaction.cuenta))
            .options(selectinload(Transaction.categoria))
            .order_by(Transaction.fecha.desc(), Transaction.created_at.desc())
        )

        if filters:
            query = query.where(and_(*filters))

        query = query.limit(limit).offset(offset)
        transactions = db.session.execute(query).scalars().all()

        return transactions, total

    def get_recent(self, limit: int = 10) -> list[Transaction]:
        """
        Get recent transactions across all accounts.

        Args:
            limit: Maximum number of results

        Returns:
            List of recent transactions
        """
        return (
            db.session.execute(
                db.select(Transaction)
                .options(selectinload(Transaction.cuenta))
                .options(selectinload(Transaction.categoria))
                .order_by(Transaction.fecha.desc(), Transaction.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
