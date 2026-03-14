"""
Transaction repository for database operations.
"""

from typing import Optional
from uuid import UUID
from datetime import date, datetime

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
            .options(selectinload(Transaction.account))
            .options(selectinload(Transaction.category))
        ).scalar_one_or_none()

    def get_by_account(
        self,
        account_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transaction]:
        """
        Get transactions for a specific account.

        Args:
            account_id: Account UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of transactions
        """
        query = (
            db.select(Transaction)
            .where(Transaction.account_id == account_id)
            .order_by(Transaction.date.desc())
        )

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return db.session.execute(query).scalars().all()

    def get_by_category(
        self,
        category_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transaction]:
        """
        Get transactions for a specific category.

        Args:
            category_id: Category UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of transactions
        """
        query = (
            db.select(Transaction)
            .where(Transaction.category_id == category_id)
            .order_by(Transaction.date.desc())
        )

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return db.session.execute(query).scalars().all()

    def get_filtered(
        self,
        account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        type: Optional[TransactionType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        tags: Optional[list[str]] = None,
        updated_since: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """
        Get transactions with filters and pagination.

        Args:
            account_id: Filter by account
            category_id: Filter by category
            type: Filter by transaction type
            date_from: Filter by start date (inclusive)
            date_to: Filter by end date (inclusive)
            tags: Filter by tags (any match)
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all matching records.
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Tuple of (list of transactions, total count)
        """
        # Build filters
        filters = []

        if account_id:
            filters.append(Transaction.account_id == account_id)
        if category_id:
            filters.append(Transaction.category_id == category_id)
        if type:
            filters.append(Transaction.type == type)
        if date_from:
            filters.append(Transaction.date >= date_from)
        if date_to:
            filters.append(Transaction.date <= date_to)
        if tags:
            # PostgreSQL array overlap operator
            filters.append(Transaction.tags.overlap(tags))
        if updated_since is not None:
            filters.append(Transaction.updated_at >= updated_since)

        # Count total matching records
        count_query = db.select(db.func.count()).select_from(Transaction)
        if filters:
            count_query = count_query.where(and_(*filters))
        total = db.session.execute(count_query).scalar()

        # Get paginated results
        query = (
            db.select(Transaction)
            .options(selectinload(Transaction.account))
            .options(selectinload(Transaction.category))
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
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
                .options(selectinload(Transaction.account))
                .options(selectinload(Transaction.category))
                .order_by(Transaction.date.desc(), Transaction.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
