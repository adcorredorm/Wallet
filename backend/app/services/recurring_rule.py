"""
RecurringRule service containing business logic for recurring rule operations.
"""

from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.recurring_rule import RecurringRule, RecurringFrequency, RecurringRuleStatus
from app.models.transaction import TransactionType
from app.repositories.recurring_rule import RecurringRuleRepository
from app.utils.exceptions import NotFoundError


class RecurringRuleService:
    """Service for recurring rule business logic."""

    def __init__(self):
        """Initialize recurring rule service with repository."""
        self.repository = RecurringRuleRepository()

    def get_by_id(self, rule_id: UUID, user_id: UUID) -> RecurringRule:
        """
        Get a recurring rule by ID scoped to the user.

        Args:
            rule_id: RecurringRule UUID.
            user_id: Owner's UUID.

        Returns:
            RecurringRule instance.

        Raises:
            NotFoundError: If not found or not owned by this user.
        """
        return self.repository.get_by_id_or_fail(rule_id, user_id)

    def get_filtered(
        self,
        user_id: UUID,
        status: str | None = None,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        updated_since: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[RecurringRule], int]:
        """
        Get recurring rules with filters and pagination.

        Args:
            user_id: Owner's UUID.
            status: Filter by status string ('active', 'paused', 'completed').
            account_id: Filter by account UUID.
            category_id: Filter by category UUID.
            updated_since: Only return rules updated at or after this timestamp.
            page: 1-indexed page number.
            limit: Items per page.

        Returns:
            Tuple of (list of rules, total count).
        """
        status_enum = RecurringRuleStatus(status) if status else None
        offset = (page - 1) * limit
        return self.repository.get_filtered(
            user_id=user_id,
            status=status_enum,
            account_id=account_id,
            category_id=category_id,
            updated_since=updated_since,
            limit=limit,
            offset=offset,
        )

    def create(
        self,
        user_id: UUID,
        offline_id: str,
        title: str,
        type: str,
        amount: Decimal,
        account_id: UUID,
        category_id: UUID,
        frequency: str,
        start_date,
        next_occurrence_date,
        interval: int = 1,
        description: str | None = None,
        tags: list[str] | None = None,
        requires_confirmation: bool = False,
        day_of_month: int | None = None,
        end_date=None,
        max_occurrences: int | None = None,
        status: str = "active",
    ) -> RecurringRule:
        """
        Create a new recurring rule.

        If a rule with the same offline_id already exists for this user, the
        existing rule is returned immediately (idempotency).

        Args:
            user_id: Owner's UUID.
            offline_id: Client-generated idempotency key.
            title: Human-readable label.
            type: Transaction type string ('income' or 'expense').
            amount: Positive amount for each generated transaction.
            account_id: Account UUID.
            category_id: Category UUID.
            frequency: Frequency string ('daily', 'weekly', 'monthly', 'yearly').
            start_date: First possible occurrence date.
            next_occurrence_date: Pre-computed next due date.
            interval: Every N periods (default 1).
            description: Optional description.
            tags: Optional tags.
            requires_confirmation: Auto (False) or verification (True) mode.
            day_of_month: 1-31 for monthly/yearly rules.
            end_date: Optional end date.
            max_occurrences: Optional occurrence limit.
            status: Initial status string (default 'active').

        Returns:
            Created or pre-existing RecurringRule instance.
        """
        existing = self.repository.get_by_offline_id(offline_id, user_id)
        if existing:
            return existing

        return self.repository.create(
            user_id=user_id,
            offline_id=offline_id,
            title=title,
            type=TransactionType(type),
            amount=amount,
            account_id=account_id,
            category_id=category_id,
            frequency=RecurringFrequency(frequency),
            start_date=start_date,
            next_occurrence_date=next_occurrence_date,
            interval=interval,
            description=description,
            tags=tags or [],
            requires_confirmation=requires_confirmation,
            day_of_month=day_of_month,
            end_date=end_date,
            max_occurrences=max_occurrences,
            occurrences_created=0,
            status=RecurringRuleStatus(status),
        )

    def update(
        self,
        rule_id: UUID,
        user_id: UUID,
        **kwargs,
    ) -> RecurringRule:
        """
        Update an existing recurring rule.

        Args:
            rule_id: RecurringRule UUID.
            user_id: Owner's UUID.
            **kwargs: Fields to update. String enum fields are converted to
                their Enum equivalents. None values are skipped.

        Returns:
            Updated RecurringRule instance.

        Raises:
            NotFoundError: If rule not found or not owned by this user.
        """
        rule = self.repository.get_by_id_or_fail(rule_id, user_id)

        update_data = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if key == "type":
                update_data[key] = TransactionType(value)
            elif key == "frequency":
                update_data[key] = RecurringFrequency(value)
            elif key == "status":
                update_data[key] = RecurringRuleStatus(value)
            else:
                update_data[key] = value

        return self.repository.update(rule, **update_data)

    def delete(self, rule_id: UUID, user_id: UUID) -> None:
        """
        Delete a recurring rule (hard delete).

        Args:
            rule_id: RecurringRule UUID.
            user_id: Owner's UUID.

        Raises:
            NotFoundError: If rule not found or not owned by this user.
        """
        rule = self.repository.get_by_id_or_fail(rule_id, user_id)
        self.repository.delete(rule)
