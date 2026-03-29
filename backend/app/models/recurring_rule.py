"""
RecurringRule model for scheduled transaction generation.

Rules define a repeating schedule. The generation engine (frontend) reads
active rules and creates real transactions on each due date.
"""

import enum
from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.models.transaction import TransactionType

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class RecurringFrequency(enum.Enum):
    """Supported repetition frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurringRuleStatus(enum.Enum):
    """Lifecycle states for a recurring rule."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class RecurringRule(BaseModel):
    """
    Recurring rule that drives scheduled transaction generation.

    Attributes:
        title: Human-readable label for the rule.
        type: Transaction type produced (income or expense).
        amount: Always positive — sign is determined by type.
        account_id: Account that receives the generated transaction.
        category_id: Category assigned to every generated transaction.
        description: Optional description copied to generated transactions.
        tags: Tags copied to generated transactions.
        requires_confirmation: False=auto (transaction created immediately),
            True=verification (PendingOccurrence created for user to confirm).
        frequency: Base time unit for the schedule.
        interval: Every N periods (e.g. interval=2, frequency=weekly → biweekly).
        day_of_month: 1–31. Used when frequency=monthly or yearly. Day overflow
            (e.g. 31 in April) handled by the frontend engine.
        start_date: First possible occurrence date.
        end_date: Optional hard stop date (inclusive).
        max_occurrences: Optional maximum number of generated transactions.
        occurrences_created: Counter incremented by the frontend engine.
        next_occurrence_date: Pre-computed next due date (advanced by engine).
        status: Current lifecycle state.
        account: Relationship to Account.
        category: Relationship to Category.
    """

    __tablename__ = "recurring_rules"

    title = Column(String(100), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    description = Column(String(500), nullable=True)
    tags = Column(ARRAY(String(50)), default=list, nullable=False)
    requires_confirmation = Column(Boolean, nullable=False, default=False)
    frequency = Column(Enum(RecurringFrequency, values_callable=lambda x: [e.value for e in x]), nullable=False)
    interval = Column(Integer, nullable=False, default=1)
    day_of_month = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    max_occurrences = Column(Integer, nullable=True)
    occurrences_created = Column(Integer, nullable=False, default=0)
    next_occurrence_date = Column(Date, nullable=False)
    status = Column(
        Enum(RecurringRuleStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RecurringRuleStatus.ACTIVE,
    )

    # Relationships
    account = relationship("Account")
    category = relationship("Category")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_recurring_rules_user_status", "user_id", "status"),
        Index("idx_recurring_rules_account", "account_id"),
        Index("idx_recurring_rules_category", "category_id"),
        UniqueConstraint("user_id", "offline_id", name="uq_recurring_rules_user_offline"),
    )

    def __repr__(self) -> str:
        """String representation of the recurring rule."""
        return f"<RecurringRule {self.title!r} {self.frequency.value} {self.status.value}>"
