"""
Pydantic schemas for ExchangeRate request validation and response serialisation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ExchangeRateResponse(BaseModel):
    """
    Schema for a single exchange rate in API responses.

    Attributes:
        currency_code: ISO 4217 or crypto ticker (e.g. 'USD', 'BTC').
        rate_to_usd: Number of units of this currency equal to 1 USD.
        source: Origin of the rate (e.g. 'exchangerate.host', 'system').
        fetched_at: Timestamp when the rate was last retrieved from source.
        updated_at: Timestamp of the last database write for this row.
    """

    currency_code: str
    rate_to_usd: Decimal
    source: str
    fetched_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExchangeRatesListResponse(BaseModel):
    """
    Schema for the list-all-rates endpoint response.

    Attributes:
        rates: All stored exchange rate rows.
        last_updated: Maximum ``fetched_at`` across all rows, or None when the
            table is empty.
    """

    rates: list[ExchangeRateResponse]
    last_updated: Optional[datetime]


class ConvertRequest(BaseModel):
    """
    Schema for a currency conversion request.

    Attributes:
        from_currency: Source currency code. Must be 3-10 uppercase ASCII letters.
        to_currency: Target currency code. Must be 3-10 uppercase ASCII letters.
        amount: Positive monetary amount to convert.
    """

    from_currency: str = Field(..., description="Source currency code (e.g. 'USD')")
    to_currency: str = Field(..., description="Target currency code (e.g. 'COP')")
    amount: Decimal = Field(..., gt=0, description="Positive amount to convert")

    @field_validator("from_currency", "to_currency")
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """Uppercase and validate the currency code format."""
        upper = v.upper()
        if not (2 <= len(upper) <= 10 and upper.isalpha()):
            raise ValueError(
                "El código de divisa debe tener entre 2 y 10 letras (ej. 'USD', 'BTC')"
            )
        return upper


class ConvertResponse(BaseModel):
    """
    Schema for a currency conversion response.

    Attributes:
        from_currency: Source currency code (uppercased).
        to_currency: Target currency code (uppercased).
        amount: Original amount in ``from_currency``.
        converted_amount: Resulting amount in ``to_currency``.
        rate: How many ``to_currency`` units equal 1 ``from_currency`` unit.
        inverse_rate: How many ``from_currency`` units equal 1 ``to_currency`` unit.
        rate_date: The ``fetched_at`` timestamp of the most recent rate row used
            in the calculation, or None if not applicable.
    """

    from_currency: str
    to_currency: str
    amount: Decimal
    converted_amount: Decimal
    rate: Decimal
    inverse_rate: Decimal
    rate_date: Optional[datetime]
