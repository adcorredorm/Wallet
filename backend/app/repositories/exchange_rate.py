"""
ExchangeRate repository for database operations.

Maintains exactly one row per currency_code. The upsert method uses a
PostgreSQL ON CONFLICT DO UPDATE so callers never need to distinguish
between insert and update.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.dialects.postgresql import insert

from app.extensions import db
from app.models.exchange_rate import ExchangeRate


class ExchangeRateRepository:
    """Repository for ExchangeRate entity operations.

    Unlike entity repositories, ExchangeRate does not extend BaseRepository
    because the primary key is a string currency_code rather than a UUID, and
    there is no client_id idempotency column on this table.
    """

    def get_all(self) -> list[ExchangeRate]:
        """
        Return all exchange rate rows ordered alphabetically by currency_code.

        Returns:
            List of ExchangeRate instances, ordered by currency_code ascending.
        """
        return (
            db.session.execute(
                db.select(ExchangeRate).order_by(ExchangeRate.currency_code)
            )
            .scalars()
            .all()
        )

    def get_by_code(self, currency_code: str) -> Optional[ExchangeRate]:
        """
        Return a single exchange rate row by its currency code.

        Args:
            currency_code: ISO 4217 or crypto ticker (e.g. 'USD', 'BTC').

        Returns:
            ExchangeRate instance if found, otherwise None.
        """
        return (
            db.session.execute(
                db.select(ExchangeRate).where(
                    ExchangeRate.currency_code == currency_code.upper()
                )
            )
            .scalars()
            .one_or_none()
        )

    def upsert(
        self,
        currency_code: str,
        rate_to_usd: Decimal,
        source: str,
        fetched_at: datetime,
    ) -> ExchangeRate:
        """
        Insert a new exchange rate row or update the existing one for the given
        currency_code.

        Uses PostgreSQL ``INSERT … ON CONFLICT (currency_code) DO UPDATE`` so
        the operation is atomic and race-condition-safe.

        Args:
            currency_code: ISO 4217 or crypto ticker. Stored and matched
                case-insensitively (uppercased before persistence).
            rate_to_usd: Number of units of this currency equal to 1 USD.
            source: Origin identifier, e.g. ``'exchangerate.host'``.
            fetched_at: Timestamp when the rate was retrieved from its source.

        Returns:
            The persisted ExchangeRate instance, refreshed from the database.
        """
        code = currency_code.upper()

        stmt = (
            insert(ExchangeRate)
            .values(
                currency_code=code,
                rate_to_usd=rate_to_usd,
                source=source,
                fetched_at=fetched_at,
            )
            .on_conflict_do_update(
                index_elements=["currency_code"],
                set_={
                    "rate_to_usd": rate_to_usd,
                    "source": source,
                    "fetched_at": fetched_at,
                    "updated_at": datetime.utcnow(),
                },
            )
        )

        db.session.execute(stmt)
        db.session.commit()

        # Re-fetch the row so the caller receives a fully hydrated ORM instance.
        row = self.get_by_code(code)
        return row  # type: ignore[return-value]  # get_by_code returns non-None after upsert
