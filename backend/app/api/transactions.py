"""
Transactions API endpoints.
"""

from datetime import date, datetime, timezone
from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionWithRelations,
    TransactionFilters,
)
from app.schemas.account import AccountResponse
from app.schemas.category import CategoryResponse
from app.services import TransactionService
from app.utils.exceptions import NotFoundError, BusinessRuleError
from app.utils.responses import success_response, error_response, paginated_response

transactions_bp = Blueprint("transactions", __name__, url_prefix="/api/v1/transactions")
transaction_service = TransactionService()


def _parse_client_updated_at(header_value: str | None) -> datetime | None:
    """
    Parse the X-Client-Updated-At header value into a UTC datetime.

    The header must be an ISO-8601 string.  Timezone-naive values are treated
    as UTC.  Returns None when the header is absent or cannot be parsed.

    Args:
        header_value: Raw header string or None

    Returns:
        Parsed datetime (UTC-aware) or None
    """
    if not header_value:
        return None
    try:
        dt = datetime.fromisoformat(header_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


@transactions_bp.route("", methods=["GET"])
def list_transactions():
    """
    List transactions with filters and pagination.

    Query Parameters:
        account_id (UUID): Filter by account
        category_id (UUID): Filter by category
        type (str): Filter by type (income, expense)
        date_from (date): Filter by start date
        date_to (date): Filter by end date
        tags (list[str]): Filter by tags (comma-separated)
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 20, max: 100)

    Returns:
        200: Paginated list of transactions
        400: Validation error
        500: Internal server error
    """
    try:
        # Parse query parameters
        filters_data = {
            "account_id": request.args.get("account_id"),
            "category_id": request.args.get("category_id"),
            "type": request.args.get("type"),
            "date_from": request.args.get("date_from"),
            "date_to": request.args.get("date_to"),
            "tags": request.args.get("tags", "").split(",") if request.args.get("tags") else None,
            "page": int(request.args.get("page", 1)),
            "limit": min(int(request.args.get("limit", 20)), 10000),
        }

        # Validate filters
        filters = TransactionFilters(**filters_data)

        # Get filtered transactions
        transactions, total = transaction_service.get_filtered(
            account_id=filters.account_id,
            category_id=filters.category_id,
            type=filters.type.value if filters.type else None,
            date_from=filters.date_from,
            date_to=filters.date_to,
            tags=filters.tags,
            page=filters.page,
            limit=filters.limit,
        )

        # Format response with relations
        items = []
        for trans in transactions:
            trans_data = TransactionResponse.model_validate(trans).model_dump(mode="json")
            trans_data["account"] = AccountResponse.model_validate(trans.account).model_dump(mode="json")
            trans_data["category"] = CategoryResponse.model_validate(trans.category).model_dump(mode="json")
            items.append(trans_data)

        return paginated_response(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.limit,
        )

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except Exception as e:
        return error_response(f"Error al listar transacciones: {str(e)}", status_code=500)


@transactions_bp.route("/<uuid:transaction_id>", methods=["GET"])
def get_transaction(transaction_id: UUID):
    """
    Get a single transaction by ID.

    Path Parameters:
        transaction_id (UUID): Transaction ID

    Returns:
        200: Transaction details with relations
        404: Transaction not found
        500: Internal server error
    """
    try:
        transaction = transaction_service.get_by_id(transaction_id)

        # Format response with relations
        data = TransactionResponse.model_validate(transaction).model_dump(mode="json")
        data["account"] = AccountResponse.model_validate(transaction.account).model_dump(mode="json")
        data["category"] = CategoryResponse.model_validate(transaction.category).model_dump(mode="json")

        return success_response(data=data)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al obtener transaccion: {str(e)}", status_code=500)


@transactions_bp.route("", methods=["POST"])
def create_transaction():
    """
    Create a new transaction.

    Request Body:
        TransactionCreate schema

    Returns:
        201: Created transaction
        400: Validation error
        404: Account or category not found
        422: Business rule violation (incompatible category type)
        500: Internal server error
    """
    try:
        # Validate request data
        transaction_data = TransactionCreate(**request.json)

        # Create transaction (idempotent when client_id is present)
        transaction = transaction_service.create(
            type=transaction_data.type.value,
            amount=transaction_data.amount,
            date=transaction_data.date,
            account_id=transaction_data.account_id,
            category_id=transaction_data.category_id,
            title=transaction_data.title,
            description=transaction_data.description,
            tags=transaction_data.tags,
            client_id=transaction_data.client_id,
            original_amount=transaction_data.original_amount,
            original_currency=transaction_data.original_currency,
            exchange_rate=transaction_data.exchange_rate,
            base_rate=transaction_data.base_rate,
        )

        data = TransactionResponse.model_validate(transaction).model_dump(mode="json")
        return success_response(
            data=data, message="Transaccion creada exitosamente", status_code=201
        )

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al crear transaccion: {str(e)}", status_code=500)


@transactions_bp.route("/<uuid:transaction_id>", methods=["PUT"])
def update_transaction(transaction_id: UUID):
    """
    Update an existing transaction.

    Supports Last-Write-Wins (LWW) conflict detection for offline-first clients.
    When the optional request header X-Client-Updated-At is present its value is
    compared against the record's server-side updated_at timestamp.  If the
    server version is more recent the update is rejected with HTTP 409 and the
    current server state is returned so the client can reconcile.

    Path Parameters:
        transaction_id (UUID): Transaction ID

    Request Headers:
        X-Client-Updated-At (str, optional): ISO-8601 timestamp of the version
            the client last observed.  Used for LWW conflict detection.

    Request Body:
        TransactionUpdate schema

    Returns:
        200: Updated transaction
        400: Validation error
        404: Transaction, account, or category not found
        409: Conflict — server version is newer than client version
        422: Business rule violation
        500: Internal server error
    """
    try:
        # Validate request data
        transaction_data = TransactionUpdate(**request.json)

        # LWW conflict detection
        client_updated_at = _parse_client_updated_at(
            request.headers.get("X-Client-Updated-At")
        )
        if client_updated_at is not None:
            current_transaction = transaction_service.get_by_id(transaction_id)
            server_updated_at = current_transaction.updated_at
            if server_updated_at.tzinfo is None:
                server_updated_at = server_updated_at.replace(tzinfo=timezone.utc)
            if server_updated_at > client_updated_at:
                server_data = TransactionResponse.model_validate(
                    current_transaction
                ).model_dump(mode="json")
                return error_response(
                    "Conflicto: el servidor tiene una version mas reciente de este recurso",
                    status_code=409,
                    errors={"server_version": server_data},
                )

        # Update transaction
        transaction = transaction_service.update(
            transaction_id=transaction_id,
            type=transaction_data.type.value if transaction_data.type else None,
            amount=transaction_data.amount,
            date=transaction_data.date,
            account_id=transaction_data.account_id,
            category_id=transaction_data.category_id,
            title=transaction_data.title,
            description=transaction_data.description,
            tags=transaction_data.tags,
            original_amount=transaction_data.original_amount,
            original_currency=transaction_data.original_currency,
            exchange_rate=transaction_data.exchange_rate,
            base_rate=transaction_data.base_rate,
        )

        data = TransactionResponse.model_validate(transaction).model_dump(mode="json")
        return success_response(data=data, message="Transaccion actualizada exitosamente")

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al actualizar transaccion: {str(e)}", status_code=500)


@transactions_bp.route("/<uuid:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id: UUID):
    """
    Delete a transaction.

    Path Parameters:
        transaction_id (UUID): Transaction ID

    Returns:
        200: Transaction deleted successfully
        404: Transaction not found
        500: Internal server error
    """
    try:
        transaction_service.delete(transaction_id)
        return success_response(message="Transaccion eliminada exitosamente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al eliminar transaccion: {str(e)}", status_code=500)
