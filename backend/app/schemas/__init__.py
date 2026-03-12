"""
Pydantic schemas package for request/response validation.

This package contains all Pydantic models used for API validation,
serialization, and documentation.
"""

from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountWithBalance,
)
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithSubcategories,
)
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionWithRelations,
    TransactionFilters,
)
from app.schemas.transfer import (
    TransferCreate,
    TransferUpdate,
    TransferResponse,
    TransferWithRelations,
    TransferFilters,
)
from app.schemas.dashboard import (
    DashboardResponse,
    NetWorthResponse,
    MonthlySummaryResponse,
)
from app.schemas.common import PaginatedResponse
from app.schemas.exchange_rate import (
    ExchangeRateResponse,
    ExchangeRatesListResponse,
    ConvertRequest,
    ConvertResponse,
)
from app.schemas.user_setting import (
    SettingUpdateRequest,
    SettingResponse,
    SettingsResponse,
)

__all__ = [
    # Account schemas
    "AccountCreate",
    "AccountUpdate",
    "AccountResponse",
    "AccountWithBalance",
    # Category schemas
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryWithSubcategories",
    # Transaction schemas
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionWithRelations",
    "TransactionFilters",
    # Transfer schemas
    "TransferCreate",
    "TransferUpdate",
    "TransferResponse",
    "TransferWithRelations",
    "TransferFilters",
    # Dashboard schemas
    "DashboardResponse",
    "NetWorthResponse",
    "MonthlySummaryResponse",
    # Common schemas
    "PaginatedResponse",
    # ExchangeRate schemas
    "ExchangeRateResponse",
    "ExchangeRatesListResponse",
    "ConvertRequest",
    "ConvertResponse",
    # UserSetting schemas
    "SettingUpdateRequest",
    "SettingResponse",
    "SettingsResponse",
]
