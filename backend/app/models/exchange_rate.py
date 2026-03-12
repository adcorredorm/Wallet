"""
ExchangeRate model for storing currency conversion rates.

Rates are expressed as units of a given currency per 1 USD.
The USD row is always present with rate_to_usd = 1.0 and source = 'system'.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, String, Numeric, DateTime, Index

from app.models.base import BaseModel


class ExchangeRate(BaseModel):
    """
    Exchange rate model keyed by currency code.

    Stores the latest known rate for each currency relative to USD.
    Only one row per currency is maintained; upserts replace the existing row.

    Attributes:
        currency_code: ISO 4217 currency code or crypto ticker (e.g. 'USD', 'BTC').
            Must be unique across the table.
        rate_to_usd: Number of units of this currency equal to 1 USD.
            For USD itself this is always 1.0.
        source: Origin of the rate — one of 'exchangerate.host', 'coingecko',
            or 'system' (for the seeded USD baseline).
        fetched_at: Timestamp when the rate was last retrieved from its source.
    """

    __tablename__ = "exchange_rates"

    currency_code = Column(String(10), nullable=False, unique=True)
    rate_to_usd = Column(Numeric(20, 10), nullable=False)
    source = Column(String(50), nullable=False)
    fetched_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_exchange_rates_currency_code", "currency_code", unique=True),
    )

    def __repr__(self) -> str:
        """String representation of the exchange rate."""
        return f"<ExchangeRate {self.currency_code} = {self.rate_to_usd} USD>"
