"""
Transfer repository for database operations.

All query methods that return user-owned data require a user_id parameter
to enforce per-user data isolation.
"""

from typing import Optional
from uuid import UUID
from datetime import date, datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Transfer
from app.repositories.base import BaseRepository


class TransferRepository(BaseRepository[Transfer]):
    """Repository for Transfer entity operations."""

    def __init__(self):
        """Initialize transfer repository."""
        super().__init__(Transfer)

    def get_with_relations(
        self, transfer_id: UUID, user_id: UUID
    ) -> Optional[Transfer]:
        """
        Get a transfer with source and destination accounts eagerly loaded,
        scoped to a user.

        Args:
            transfer_id: Transfer UUID.
            user_id: Owner's UUID.

        Returns:
            Transfer instance with relations or None.
        """
        return db.session.execute(
            db.select(Transfer)
            .where(
                Transfer.id == transfer_id,
                Transfer.user_id == user_id,
            )
            .options(selectinload(Transfer.source_account))
            .options(selectinload(Transfer.destination_account))
        ).scalar_one_or_none()

    def get_by_account(
        self,
        account_id: UUID,
        user_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transfer]:
        """
        Get transfers involving a specific account (as source or destination),
        scoped to a user.

        Args:
            account_id: Account UUID.
            user_id: Owner's UUID.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of transfers.
        """
        query = (
            db.select(Transfer)
            .where(
                Transfer.user_id == user_id,
                or_(
                    Transfer.source_account_id == account_id,
                    Transfer.destination_account_id == account_id,
                ),
            )
            .order_by(Transfer.date.desc())
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
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        tags: Optional[list[str]] = None,
        updated_since: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Transfer], int]:
        """
        Get transfers with filters and pagination, scoped to a user.

        Args:
            user_id: Owner's UUID. Required — only transfers for this user
                are returned.
            account_id: Filter by account (source or destination).
            date_from: Filter by start date (inclusive).
            date_to: Filter by end date (inclusive).
            tags: Filter by tags (any match).
            updated_since: Only return records with updated_at >= updated_since
                (naive UTC). None returns all matching records.
            limit: Maximum results per page.
            offset: Number of results to skip.

        Returns:
            Tuple of (list of transfers, total count).
        """
        filters = [Transfer.user_id == user_id]

        if account_id:
            filters.append(
                or_(
                    Transfer.source_account_id == account_id,
                    Transfer.destination_account_id == account_id,
                )
            )
        if date_from:
            filters.append(Transfer.date >= date_from)
        if date_to:
            filters.append(Transfer.date <= date_to)
        if tags:
            filters.append(Transfer.tags.overlap(tags))
        if updated_since is not None:
            filters.append(Transfer.updated_at >= updated_since)

        count_query = db.select(db.func.count()).select_from(Transfer)
        count_query = count_query.where(and_(*filters))
        total = db.session.execute(count_query).scalar()

        query = (
            db.select(Transfer)
            .options(selectinload(Transfer.source_account))
            .options(selectinload(Transfer.destination_account))
            .order_by(Transfer.date.desc(), Transfer.created_at.desc())
        )
        query = query.where(and_(*filters))
        query = query.limit(limit).offset(offset)
        transfers = db.session.execute(query).scalars().all()

        return transfers, total

    def get_recent(self, user_id: UUID, limit: int = 10) -> list[Transfer]:
        """
        Get recent transfers for a user.

        Args:
            user_id: Owner's UUID.
            limit: Maximum number of results.

        Returns:
            List of recent transfers.
        """
        return (
            db.session.execute(
                db.select(Transfer)
                .where(Transfer.user_id == user_id)
                .options(selectinload(Transfer.source_account))
                .options(selectinload(Transfer.destination_account))
                .order_by(Transfer.date.desc(), Transfer.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
