"""
Repository package for data access layer.

Repositories encapsulate database queries and provide a clean interface
for services to interact with the database.
"""

from app.repositories.account import AccountRepository
from app.repositories.category import CategoryRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.transfer import TransferRepository
from app.repositories.exchange_rate import ExchangeRateRepository
from app.repositories.user_setting import SettingsRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.recurring_rule import RecurringRuleRepository

__all__ = [
    "AccountRepository",
    "CategoryRepository",
    "TransactionRepository",
    "TransferRepository",
    "ExchangeRateRepository",
    "SettingsRepository",
    "DashboardRepository",
    "RecurringRuleRepository",
]
