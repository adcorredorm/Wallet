# backend/app/services/budget.py
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.models.budget import Budget, BudgetFrequency, BudgetStatus, BudgetType
from app.repositories.budget import BudgetRepository
from app.utils.exceptions import NotFoundError


class BudgetService:
    def __init__(self):
        self.repository = BudgetRepository()

    def get_by_id(self, budget_id: UUID, user_id: UUID) -> Budget:
        return self.repository.get_by_id_or_fail(budget_id, user_id)

    def get_active(
        self,
        user_id: UUID,
        updated_since: datetime | None = None,
    ) -> list[Budget]:
        return self.repository.get_active(user_id=user_id, updated_since=updated_since)

    def create(
        self,
        user_id: UUID,
        offline_id: str,
        name: str,
        amount_limit: Decimal,
        currency: str,
        budget_type: str,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        frequency: str | None = None,
        interval: int = 1,
        reference_date: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str = "active",
        icon: str | None = None,
        color: str | None = None,
    ) -> Budget:
        existing = self.repository.get_by_offline_id(offline_id, user_id)
        if existing:
            return existing

        return self.repository.create(
            user_id=user_id,
            offline_id=offline_id,
            name=name,
            account_id=account_id,
            category_id=category_id,
            amount_limit=amount_limit,
            currency=currency,
            budget_type=BudgetType(budget_type),
            frequency=BudgetFrequency(frequency) if frequency else None,
            interval=interval,
            reference_date=reference_date,
            start_date=start_date,
            end_date=end_date,
            status=BudgetStatus(status),
            icon=icon,
            color=color,
        )

    def update(self, budget_id: UUID, user_id: UUID, **kwargs) -> Budget:
        budget = self.repository.get_by_id_or_fail(budget_id, user_id)
        update_data = {}
        for key, value in kwargs.items():
            if value is None:
                continue
            if key == "frequency":
                update_data[key] = BudgetFrequency(value)
            elif key == "status":
                update_data[key] = BudgetStatus(value)
            else:
                update_data[key] = value
        return self.repository.update(budget, **update_data)

    def archive(self, budget_id: UUID, user_id: UUID) -> Budget:
        budget = self.repository.get_by_id_or_fail(budget_id, user_id)
        return self.repository.archive(budget)

    def delete(self, budget_id: UUID, user_id: UUID) -> None:
        budget = self.repository.get_by_id_or_fail(budget_id, user_id)
        self.repository.delete(budget)
