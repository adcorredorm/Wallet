"""
CLI commands for managing exchange rates.

Provides the ``flask rates update`` command, which fetches current fiat and
crypto exchange rates from free public APIs and upserts them into the
``exchange_rates`` table.

Sources:
    - Fiat:   https://open.er-api.com/v6/latest/USD  (no API key required)
    - Crypto: https://api.coingecko.com/api/v3/simple/price  (no API key required)

Rate semantics:
    ``rate_to_usd`` stores "units of this currency per 1 USD".
    For fiat the API already returns that value directly.
    For crypto the API returns "USD per 1 coin", so we store the reciprocal.
"""

import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import click
import requests
from flask import Blueprint

from app.extensions import db
from app.models.exchange_rate import ExchangeRate


# ---------------------------------------------------------------------------
# Blueprint — the name "rates" makes the CLI group "flask rates ..."
# ---------------------------------------------------------------------------

rates_bp = Blueprint("rates", __name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIAT_API_URL = "https://open.er-api.com/v6/latest/USD"
CRYPTO_API_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin,ethereum&vs_currencies=usd"
)

REQUIRED_FIAT_CURRENCIES: frozenset[str] = frozenset(
    {"COP", "USD", "EUR", "BRL", "JPY", "ARS", "GBP"}
)

# Maps CoinGecko coin ID → canonical ticker stored in the DB
CRYPTO_ID_TO_TICKER: dict[str, str] = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
}

FIAT_SOURCE = "open.er-api.com"
CRYPTO_SOURCE = "coingecko"

REQUEST_TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _upsert_rate(
    currency_code: str,
    rate: Decimal,
    source: str,
    fetched_at: datetime,
) -> None:
    """
    Insert or update a single exchange rate row.

    If a row for ``currency_code`` already exists it is updated in-place;
    otherwise a new row is inserted.  The caller is responsible for calling
    ``db.session.commit()`` after all upserts are complete.

    Args:
        currency_code: ISO 4217 code or crypto ticker (e.g. ``'EUR'``, ``'BTC'``).
        rate: Units of ``currency_code`` per 1 USD.
        source: Human-readable identifier for the data source.
        fetched_at: Timestamp at which the rate was retrieved.
    """
    existing: Optional[ExchangeRate] = ExchangeRate.query.filter_by(
        currency_code=currency_code
    ).first()

    if existing:
        existing.rate_to_usd = rate
        existing.source = source
        existing.fetched_at = fetched_at
    else:
        db.session.add(
            ExchangeRate(
                currency_code=currency_code,
                rate_to_usd=rate,
                source=source,
                fetched_at=fetched_at,
            )
        )


def _fetch_fiat_rates() -> dict[str, Decimal]:
    """
    Fetch fiat exchange rates from open.er-api.com.

    Returns rates as a mapping of currency code → units per 1 USD.
    Always includes ``USD`` with a rate of ``Decimal('1.0')``.

    Returns:
        Dictionary mapping currency code strings to Decimal rate values.

    Raises:
        requests.RequestException: If the HTTP request fails.
        KeyError: If the expected ``rates`` key is absent from the response.
        ValueError: If the response cannot be parsed as JSON.
    """
    response = requests.get(FIAT_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    payload: dict = response.json()
    raw_rates: dict[str, float] = payload["rates"]

    result: dict[str, Decimal] = {
        code: Decimal(str(value))
        for code, value in raw_rates.items()
        if code in REQUIRED_FIAT_CURRENCIES
    }

    # Guarantee USD is always present even if the API omits it
    result["USD"] = Decimal("1.0")

    return result


def _fetch_crypto_rates() -> dict[str, Decimal]:
    """
    Fetch cryptocurrency prices from the CoinGecko free API and convert to
    ``rate_to_usd`` format (units of currency per 1 USD, i.e. 1 / price_in_usd).

    Returns:
        Dictionary mapping ticker symbol strings (e.g. ``'BTC'``) to Decimal
        rate values representing units of that currency per 1 USD.

    Raises:
        requests.RequestException: If the HTTP request fails.
        ValueError: If the response cannot be parsed as JSON or a price is zero.
    """
    response = requests.get(CRYPTO_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    payload: dict = response.json()
    result: dict[str, Decimal] = {}

    for coin_id, ticker in CRYPTO_ID_TO_TICKER.items():
        price_usd: float = payload[coin_id]["usd"]
        if price_usd == 0:
            raise ValueError(
                f"CoinGecko returned a zero price for {coin_id} — skipping to avoid division by zero"
            )
        result[ticker] = Decimal("1") / Decimal(str(price_usd))

    return result


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


@rates_bp.cli.command("update")
def update_rates() -> None:
    """Fetch and update exchange rates from external APIs.

    Queries open.er-api.com for fiat currencies and CoinGecko for BTC/ETH.
    Each fetched rate is upserted into the exchange_rates table.

    Partial success is tolerated: if one source fails the rates from the
    other source are still persisted and the command exits with code 0.
    If both sources fail the command exits with a non-zero code.
    """
    now: datetime = datetime.now(tz=timezone.utc)
    fiat_rates: dict[str, Decimal] = {}
    crypto_rates: dict[str, Decimal] = {}
    fiat_ok = False
    crypto_ok = False

    # --- Fetch fiat ---
    try:
        fiat_rates = _fetch_fiat_rates()
        fiat_ok = True
        click.echo(f"Fetched {len(fiat_rates)} fiat rate(s) from {FIAT_API_URL}")
    except Exception as exc:  # noqa: BLE001
        click.echo(f"[ERROR] Failed to fetch fiat rates: {exc}", err=True)

    # --- Fetch crypto ---
    try:
        crypto_rates = _fetch_crypto_rates()
        crypto_ok = True
        click.echo(f"Fetched {len(crypto_rates)} crypto rate(s) from CoinGecko")
    except Exception as exc:  # noqa: BLE001
        click.echo(f"[ERROR] Failed to fetch crypto rates: {exc}", err=True)

    # --- Both failed ---
    if not fiat_ok and not crypto_ok:
        click.echo("[ERROR] All rate sources failed. No data written.", err=True)
        sys.exit(1)

    # --- Upsert whatever succeeded ---
    upserted_count = 0

    for code, rate in fiat_rates.items():
        _upsert_rate(code, rate, FIAT_SOURCE, now)
        upserted_count += 1

    for code, rate in crypto_rates.items():
        _upsert_rate(code, rate, CRYPTO_SOURCE, now)
        upserted_count += 1

    db.session.commit()
    click.echo(f"Successfully upserted {upserted_count} exchange rate(s).")
