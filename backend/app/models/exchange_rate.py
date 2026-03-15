"""
ExchangeRate model for storing currency conversion rates.

Rates are expressed as units of a given currency per 1 USD.
The USD row is always present with rate_to_usd = 1.0 and source = 'system'.

ExchangeRate is global reference data — it has no user_id and does NOT inherit
from BaseModel (which injects user_id). Only the minimal common columns (id,
created_at, updated_at) are declared here.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class ExchangeRate(db.Model):
    """
    Exchange rate model keyed by currency code.

    Stores the latest known rate for each currency relative to USD.
    Only one row per currency is maintained; upserts replace the existing row.
    This table is global (not per-user), so there is no user_id column.

    Attributes:
        id: UUID primary key generated server-side.
        currency_code: ISO 4217 currency code or crypto ticker (e.g. 'USD', 'BTC').
            Must be unique across the table.
        rate_to_usd: Number of units of this currency equal to 1 USD.
            For USD itself this is always 1.0.
        source: Origin of the rate — one of 'exchangerate.host', 'coingecko',
            or 'system' (for the seeded USD baseline).
        fetched_at: Timestamp when the rate was last retrieved from its source.
        created_at: UTC timestamp of row creation.
        updated_at: UTC timestamp of last update.
    """

    __tablename__ = "exchange_rates"
    __allow_unmapped__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    currency_code = Column(String(10), nullable=False, unique=True)
    rate_to_usd = Column(Numeric(20, 10), nullable=False)
    source = Column(String(50), nullable=False)
    fetched_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_exchange_rates_currency_code", "currency_code", unique=True),
    )

    def __repr__(self) -> str:
        """String representation of the exchange rate."""
        return f"<ExchangeRate {self.currency_code} = {self.rate_to_usd} USD>"
