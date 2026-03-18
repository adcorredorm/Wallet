"""
Internal API endpoints — not exposed to regular users.

These endpoints are called by automated systems (e.g. GitHub Actions cron jobs)
and are protected by a static Bearer token stored in CRON_SECRET_TOKEN.
"""

import os

from flask import Blueprint, current_app, request

from app.cli.rates import _fetch_crypto_rates, _fetch_fiat_rates, _upsert_rate
from app.extensions import db

internal_bp = Blueprint("internal", __name__, url_prefix="/internal")


def _check_cron_token() -> bool:
    """Return True if the request carries a valid cron Bearer token."""
    token = current_app.config.get("CRON_SECRET_TOKEN", "")
    if not token:
        return False
    auth_header = request.headers.get("Authorization", "")
    return auth_header == f"Bearer {token}"


@internal_bp.post("/rates/update")
def update_rates():
    """Trigger an exchange-rate refresh.

    Called daily by GitHub Actions. Reuses the same fetch+upsert logic as
    ``flask rates update`` CLI command.

    Returns 200 on full or partial success, 401 on auth failure, 502 if all
    external rate sources fail.
    """
    if not _check_cron_token():
        return {"error": "Unauthorized"}, 401

    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)

    fiat_ok = False
    crypto_ok = False
    upserted = 0
    errors = []

    try:
        fiat_rates = _fetch_fiat_rates()
        for code, rate in fiat_rates.items():
            _upsert_rate(code, rate, "open.er-api.com", now)
            upserted += 1
        fiat_ok = True
    except Exception as exc:
        errors.append(f"fiat: {exc}")

    try:
        crypto_rates = _fetch_crypto_rates()
        for code, rate in crypto_rates.items():
            _upsert_rate(code, rate, "coingecko", now)
            upserted += 1
        crypto_ok = True
    except Exception as exc:
        errors.append(f"crypto: {exc}")

    if not fiat_ok and not crypto_ok:
        return {"error": "All rate sources failed", "details": errors}, 502

    db.session.commit()
    return {
        "upserted": upserted,
        "fiat_ok": fiat_ok,
        "crypto_ok": crypto_ok,
        "errors": errors,
    }, 200
