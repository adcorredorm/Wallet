"""
Exchange rates API endpoints.

Provides read-only access to stored exchange rates and currency conversion.
All write operations on rates are performed by background jobs, not through
this API.
"""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError

from app.schemas.exchange_rate import (
    ConvertResponse,
    ExchangeRateResponse,
    ExchangeRatesListResponse,
)
from app.services.exchange_rate import ExchangeRateService
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.responses import error_response, success_response

exchange_rates_bp = Blueprint("exchange_rates", __name__, url_prefix="/api/v1")
exchange_rate_service = ExchangeRateService()


@exchange_rates_bp.route("/exchange-rates", methods=["GET"])
def list_exchange_rates():
    """
    List all stored exchange rates.

    Returns every exchange rate row ordered alphabetically by currency code,
    together with the most recent ``fetched_at`` timestamp across all rows.
    Always returns 200 — the ``rates`` list is empty when no rates have been
    loaded yet.

    Returns:
        200: ExchangeRatesListResponse payload.
        500: Internal server error.
    """
    try:
        rates = exchange_rate_service.get_all()
        last_updated = exchange_rate_service.get_last_updated()

        response = ExchangeRatesListResponse(
            rates=[ExchangeRateResponse.model_validate(r) for r in rates],
            last_updated=last_updated,
        )

        return success_response(data=response.model_dump(mode="json"))

    except Exception as e:
        return error_response(
            f"Error al obtener tipos de cambio: {str(e)}", status_code=500
        )


@exchange_rates_bp.route("/exchange-rates/convert", methods=["GET"])
def convert_currency():
    """
    Convert an amount from one currency to another.

    Query Parameters:
        from (str, required): Source currency code (e.g. ``USD``).
        to (str, required): Target currency code (e.g. ``COP``).
        amount (decimal, required): Positive monetary amount to convert.

    Returns:
        200: ConvertResponse with ``rate``, ``inverse_rate``,
             ``converted_amount``, and ``rate_date``.
        404: One or both currency codes are not in the exchange-rate table.
        422: Missing or invalid query parameters.
        500: Internal server error.
    """
    try:
        from_code = request.args.get("from")
        to_code = request.args.get("to")
        amount_raw = request.args.get("amount")

        # --- Parameter presence validation ---
        missing = [p for p, v in [("from", from_code), ("to", to_code), ("amount", amount_raw)] if not v]
        if missing:
            return error_response(
                f"Parámetros requeridos faltantes: {', '.join(missing)}",
                status_code=422,
            )

        # --- Amount parsing ---
        try:
            amount = Decimal(amount_raw)  # type: ignore[arg-type]
        except InvalidOperation:
            return error_response(
                "El parámetro 'amount' debe ser un número decimal válido (ej. '100.50')",
                status_code=422,
            )

        if amount <= Decimal("0"):
            return error_response(
                "El parámetro 'amount' debe ser un valor positivo mayor que cero",
                status_code=422,
            )

        # --- Currency code format validation ---
        from_upper = from_code.upper()  # type: ignore[union-attr]
        to_upper = to_code.upper()  # type: ignore[union-attr]

        for label, code in [("from", from_upper), ("to", to_upper)]:
            if not (2 <= len(code) <= 10 and code.isalpha()):
                return error_response(
                    f"El código de divisa '{label}' debe tener entre 2 y 10 letras "
                    "(ej. 'USD', 'BTC')",
                    status_code=422,
                )

        # --- Perform conversion ---
        converted_amount = exchange_rate_service.convert(
            amount=amount,
            from_currency=from_upper,
            to_currency=to_upper,
        )

        # Build a lookup dict from all rates so we can derive rate metadata
        # without reaching into the repository layer from the route.
        all_rates = {r.currency_code: r for r in exchange_rate_service.get_all()}

        from_row = all_rates.get(from_upper)
        to_row = all_rates.get(to_upper)

        # Compute cross rates via USD triangulation:
        #   rate = rate_to / rate_from  (units of to_currency per 1 from_currency)
        from_rate_usd = Decimal(str(from_row.rate_to_usd))  # type: ignore[union-attr]
        to_rate_usd = Decimal(str(to_row.rate_to_usd))  # type: ignore[union-attr]

        if from_upper == to_upper:
            rate = Decimal("1")
            inverse_rate = Decimal("1")
        else:
            rate = (to_rate_usd / from_rate_usd).quantize(Decimal("0.0000000001"))
            inverse_rate = (from_rate_usd / to_rate_usd).quantize(Decimal("0.0000000001"))

        # rate_date is the older of the two rows' fetched_at timestamps —
        # the conversion is only as fresh as its least-recently-updated rate.
        rate_date = min(
            from_row.fetched_at,  # type: ignore[union-attr]
            to_row.fetched_at,  # type: ignore[union-attr]
        ) if from_upper != to_upper else from_row.fetched_at  # type: ignore[union-attr]

        response = ConvertResponse(
            from_currency=from_upper,
            to_currency=to_upper,
            amount=amount,
            converted_amount=converted_amount,
            rate=rate,
            inverse_rate=inverse_rate,
            rate_date=rate_date,
        )

        return success_response(data=response.model_dump(mode="json"))

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except ValidationError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(
            f"Error al convertir divisa: {str(e)}", status_code=500
        )
