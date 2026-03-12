"""
ExchangeRate service containing business logic for currency conversion.

All arithmetic uses Python's ``decimal.Decimal`` to avoid floating-point
rounding errors when dealing with financial amounts.

Triangulation via USD
---------------------
Every rate is stored as "units of currency per 1 USD".  To convert from
currency A to currency B:

    amount_B = amount_A * (rate_B / rate_A)

where rate_A and rate_B are the respective ``rate_to_usd`` values.  For USD
itself the stored rate is always 1.0 (seeded by the system).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.models.exchange_rate import ExchangeRate
from app.repositories.exchange_rate import ExchangeRateRepository
from app.utils.exceptions import NotFoundError


class ExchangeRateService:
    """Service for exchange rate retrieval and currency conversion."""

    def __init__(self) -> None:
        """Initialise service with its repository."""
        self.repository = ExchangeRateRepository()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_all(self) -> list[ExchangeRate]:
        """
        Return all stored exchange rates ordered by currency code.

        Returns:
            List of ExchangeRate instances.
        """
        return self.repository.get_all()

    def get_last_updated(self) -> Optional[datetime]:
        """
        Return the most recent ``fetched_at`` timestamp across all rate rows.

        Returns:
            A datetime if at least one rate exists, otherwise None.
        """
        rates = self.repository.get_all()
        if not rates:
            return None
        return max(r.fetched_at for r in rates)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """
        Convert an amount from one currency to another via USD triangulation.

        The formula is::

            amount_to = amount_from * (rate_to / rate_from)

        where each ``rate`` is the number of units of that currency per 1 USD.

        Args:
            amount: Positive monetary amount in ``from_currency``.
            from_currency: Source currency code (case-insensitive).
            to_currency: Target currency code (case-insensitive).

        Returns:
            Converted amount as a Decimal, rounded to 10 decimal places.

        Raises:
            NotFoundError: If ``from_currency`` or ``to_currency`` has no rate
                row in the database.
        """
        from_code = from_currency.upper()
        to_code = to_currency.upper()

        if from_code == to_code:
            return amount

        from_rate_row = self.repository.get_by_code(from_code)
        if from_rate_row is None:
            raise NotFoundError("ExchangeRate", from_code)

        to_rate_row = self.repository.get_by_code(to_code)
        if to_rate_row is None:
            raise NotFoundError("ExchangeRate", to_code)

        from_rate = Decimal(str(from_rate_row.rate_to_usd))
        to_rate = Decimal(str(to_rate_row.rate_to_usd))

        # Triangulate via USD: amount_B = amount_A * (rate_B / rate_A)
        converted = amount * (to_rate / from_rate)
        return converted.quantize(Decimal("0.0000000001"))

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def upsert_rate(
        self,
        currency_code: str,
        rate_to_usd: Decimal,
        source: str,
        fetched_at: datetime,
    ) -> ExchangeRate:
        """
        Insert or update the exchange rate for a given currency code.

        Args:
            currency_code: ISO 4217 or crypto ticker (stored uppercased).
            rate_to_usd: Number of units of this currency equal to 1 USD.
            source: Origin of the rate (e.g. ``'exchangerate.host'``).
            fetched_at: Timestamp when the rate was retrieved from its source.

        Returns:
            Persisted ExchangeRate instance.
        """
        return self.repository.upsert(
            currency_code=currency_code,
            rate_to_usd=rate_to_usd,
            source=source,
            fetched_at=fetched_at,
        )
