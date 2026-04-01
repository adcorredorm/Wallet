"""
Budget model for spending limits per account or category.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category


class BudgetType(enum.Enum):
    RECURRING = "recurring"
    ONE_TIME = "one_time"


class BudgetStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class BudgetFrequency(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Budget(BaseModel):
    __tablename__ = "budgets"

    name = Column(String(100), nullable=False)
    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
    )
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
    )
    amount_limit = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(3), nullable=False)
    budget_type = Column(
        Enum(BudgetType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    frequency = Column(
        Enum(BudgetFrequency, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    interval = Column(Integer, nullable=True, default=1)
    reference_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(
        Enum(BudgetStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=BudgetStatus.ACTIVE,
    )
    icon = Column(String(50), nullable=True)
    color = Column(String(7), nullable=True)

    account: "Account" = relationship("Account")
    category: "Category" = relationship("Category")

    __table_args__ = (
        CheckConstraint(
            "(account_id IS NULL) != (category_id IS NULL)",
            name="ck_budget_scope_xor",
        ),
        Index("idx_budgets_user_status", "user_id", "status"),
        Index("idx_budgets_account", "account_id"),
        Index("idx_budgets_category", "category_id"),
        UniqueConstraint("user_id", "offline_id", name="uq_budgets_user_offline"),
    )

    def __repr__(self) -> str:
        return f"<Budget {self.name!r} {self.budget_type.value} {self.status.value}>"
