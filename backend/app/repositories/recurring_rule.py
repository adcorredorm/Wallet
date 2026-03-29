"""
RecurringRule repository for database operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_

from app.extensions import db
from app.models.recurring_rule import RecurringRule, RecurringRuleStatus
from app.repositories.base import BaseRepository


class RecurringRuleRepository(BaseRepository[RecurringRule]):
    """Repository for RecurringRule entity operations."""

    def __init__(self):
        super().__init__(RecurringRule)

    def get_filtered(
        self,
        user_id: UUID,
        status: Optional[RecurringRuleStatus] = None,
        account_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        updated_since: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RecurringRule], int]:
        """
        Get recurring rules with optional filters, scoped to a user.

        Args:
            user_id: Owner's UUID.
            status: Filter by lifecycle status.
            account_id: Filter by account.
            category_id: Filter by category.
            updated_since: Only return records modified at or after this timestamp
                (naive UTC). None returns all records.
            limit: Maximum results per page.
            offset: Number of results to skip.

        Returns:
            Tuple of (list of rules, total count).
        """
        filters = [RecurringRule.user_id == user_id]

        if status is not None:
            filters.append(RecurringRule.status == status)
        if account_id is not None:
            filters.append(RecurringRule.account_id == account_id)
        if category_id is not None:
            filters.append(RecurringRule.category_id == category_id)
        if updated_since is not None:
            filters.append(RecurringRule.updated_at >= updated_since)

        count_query = (
            db.select(db.func.count())
            .select_from(RecurringRule)
            .where(and_(*filters))
        )
        total = db.session.execute(count_query).scalar()

        query = (
            db.select(RecurringRule)
            .where(and_(*filters))
            .order_by(RecurringRule.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rules = db.session.execute(query).scalars().all()

        return rules, total
