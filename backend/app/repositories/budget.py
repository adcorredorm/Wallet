# backend/app/repositories/budget.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_

from app.extensions import db
from app.models.budget import Budget, BudgetStatus
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self):
        super().__init__(Budget)

    def get_active(
        self,
        user_id: UUID,
        updated_since: Optional[datetime] = None,
    ) -> list[Budget]:
        filters = [Budget.user_id == user_id]
        if updated_since is not None:
            filters.append(Budget.updated_at >= updated_since)
        else:
            filters.append(Budget.status != BudgetStatus.ARCHIVED)

        query = (
            db.select(Budget)
            .where(and_(*filters))
            .order_by(Budget.created_at.desc())
        )
        return db.session.execute(query).scalars().all()

    def archive(self, budget: Budget) -> Budget:
        budget.status = BudgetStatus.ARCHIVED
        db.session.commit()
        db.session.refresh(budget)
        return budget
