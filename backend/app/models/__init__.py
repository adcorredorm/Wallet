"""
SQLAlchemy models package.

This package contains all database models for the Wallet application.
"""

from app.models.base import BaseModel
from app.models.account import Account, AccountType
from app.models.category import Category, CategoryType
from app.models.transaction import Transaction, TransactionType
from app.models.transfer import Transfer
from app.models.exchange_rate import ExchangeRate
from app.models.user_setting import UserSetting
from app.models.dashboard import Dashboard
from app.models.dashboard_widget import DashboardWidget, WidgetType

__all__ = [
    "BaseModel",
    "Account",
    "AccountType",
    "Category",
    "CategoryType",
    "Transaction",
    "TransactionType",
    "Transfer",
    "ExchangeRate",
    "UserSetting",
    "Dashboard",
    "DashboardWidget",
    "WidgetType",
]
