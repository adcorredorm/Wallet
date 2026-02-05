"""
Transfer repository for database operations.
"""

from typing import Optional
from uuid import UUID
from datetime import date

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

    def get_with_relations(self, transfer_id: UUID) -> Optional[Transfer]:
        """
        Get a transfer with source and destination accounts eagerly loaded.

        Args:
            transfer_id: Transfer UUID

        Returns:
            Transfer instance with relations or None
        """
        return db.session.execute(
            db.select(Transfer)
            .where(Transfer.id == transfer_id)
            .options(selectinload(Transfer.cuenta_origen))
            .options(selectinload(Transfer.cuenta_destino))
        ).scalar_one_or_none()

    def get_by_account(
        self,
        cuenta_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[Transfer]:
        """
        Get transfers involving a specific account (as source or destination).

        Args:
            cuenta_id: Account UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of transfers
        """
        query = (
            db.select(Transfer)
            .where(
                or_(
                    Transfer.cuenta_origen_id == cuenta_id,
                    Transfer.cuenta_destino_id == cuenta_id,
                )
            )
            .order_by(Transfer.fecha.desc())
        )

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        return db.session.execute(query).scalars().all()

    def get_filtered(
        self,
        cuenta_id: Optional[UUID] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        tags: Optional[list[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Transfer], int]:
        """
        Get transfers with filters and pagination.

        Args:
            cuenta_id: Filter by account (source or destination)
            fecha_desde: Filter by start date (inclusive)
            fecha_hasta: Filter by end date (inclusive)
            tags: Filter by tags (any match)
            limit: Maximum results per page
            offset: Number of results to skip

        Returns:
            Tuple of (list of transfers, total count)
        """
        # Build filters
        filters = []

        if cuenta_id:
            filters.append(
                or_(
                    Transfer.cuenta_origen_id == cuenta_id,
                    Transfer.cuenta_destino_id == cuenta_id,
                )
            )
        if fecha_desde:
            filters.append(Transfer.fecha >= fecha_desde)
        if fecha_hasta:
            filters.append(Transfer.fecha <= fecha_hasta)
        if tags:
            # PostgreSQL array overlap operator
            filters.append(Transfer.tags.overlap(tags))

        # Count total matching records
        count_query = db.select(db.func.count()).select_from(Transfer)
        if filters:
            count_query = count_query.where(and_(*filters))
        total = db.session.execute(count_query).scalar()

        # Get paginated results
        query = (
            db.select(Transfer)
            .options(selectinload(Transfer.cuenta_origen))
            .options(selectinload(Transfer.cuenta_destino))
            .order_by(Transfer.fecha.desc(), Transfer.created_at.desc())
        )

        if filters:
            query = query.where(and_(*filters))

        query = query.limit(limit).offset(offset)
        transfers = db.session.execute(query).scalars().all()

        return transfers, total

    def get_recent(self, limit: int = 10) -> list[Transfer]:
        """
        Get recent transfers across all accounts.

        Args:
            limit: Maximum number of results

        Returns:
            List of recent transfers
        """
        return (
            db.session.execute(
                db.select(Transfer)
                .options(selectinload(Transfer.cuenta_origen))
                .options(selectinload(Transfer.cuenta_destino))
                .order_by(Transfer.fecha.desc(), Transfer.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
