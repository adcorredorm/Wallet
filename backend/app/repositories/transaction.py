"""
Transaction repository for database operations.

All query methods that return user-owned data require a user_id parameter
to enforce per-user data isolation.
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

    def get_with_relations(
        self, transaction_id: UUID, user_id: UUID
    ) -> Optional[Transaction]:
        """
        Get a transaction with account and category eagerly loaded, scoped to a user.

        Args:
            transaction_id: Transaction UUID.
            user_id: Owner's UUID.

        Returns:
            Transaction instance with relations or None.
        """
        return db.session.execute(
            db.select(Transaction)
            .where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
            .options(selectinload(Transaction.account))
            .options(selectinload(Transaction.category))
        ).scalar_one_or_none()

    def get_by_account(
        self,
        account_id: UUID,
        user_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transaction]:
        """
        Get transactions for a specific account, scoped to a user.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of transactions.
        """
        query = (
            db.select(Transaction)
            .where(
                Transaction.account_id == account_id,
                Transaction.user_id == user_id,
            )
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
        user_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transaction]:
        """
        Get transactions for a specific category, scoped to a user.

        Args:
            category_id: Category UUID.
            user_id: Owner's UUID.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of transactions.
        """
        query = (
            db.select(Transaction)
            .where(
                Transaction.category_id == category_id,
                Transaction.user_id == user_id,
            )
            .order_by(Transaction.date.desc())
        )

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return db.session.execute(query).scalars().all()

    def get_filtered(
        self,
        user_id: UUID,
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
        Get transactions with filters and pagination, scoped to a user.

        Args:
            user_id: Owner's UUID. Required — only transactions for this user
                are returned.
            account_id: Filter by account.
            category_id: Filter by category.
            type: Filter by transaction type.
            date_from: Filter by start date (inclusive).
            date_to: Filter by end date (inclusive).
            tags: Filter by tags (any match).
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all matching records.
            limit: Maximum results per page.
            offset: Number of results to skip.

        Returns:
            Tuple of (list of transactions, total count).
        """
        filters = [Transaction.user_id == user_id]

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
            filters.append(Transaction.tags.overlap(tags))
        if updated_since is not None:
            filters.append(Transaction.updated_at >= updated_since)

        count_query = db.select(db.func.count()).select_from(Transaction)
        count_query = count_query.where(and_(*filters))
        total = db.session.execute(count_query).scalar()

        query = (
            db.select(Transaction)
            .options(selectinload(Transaction.account))
            .options(selectinload(Transaction.category))
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        )
        query = query.where(and_(*filters))
        query = query.limit(limit).offset(offset)
        transactions = db.session.execute(query).scalars().all()

        return transactions, total

    def get_recent(self, user_id: UUID, limit: int = 10) -> list[Transaction]:
        """
        Get recent transactions for a user.

        Args:
            user_id: Owner's UUID.
            limit: Maximum number of results.

        Returns:
            List of recent transactions.
        """
        return (
            db.session.execute(
                db.select(Transaction)
                .where(Transaction.user_id == user_id)
                .options(selectinload(Transaction.account))
                .options(selectinload(Transaction.category))
                .order_by(Transaction.date.desc(), Transaction.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
