"""
Transfers API endpoints.
"""

from datetime import datetime, timezone
from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.schemas.transfer import (
    TransferCreate,
    TransferUpdate,
    TransferResponse,
    TransferWithRelations,
    TransferFilters,
)
from app.schemas.account import AccountResponse
from app.services import TransferService
from app.utils.exceptions import NotFoundError, BusinessRuleError, ValidationError
from app.utils.responses import success_response, error_response, paginated_response

transfers_bp = Blueprint("transfers", __name__, url_prefix="/api/v1/transfers")
transfer_service = TransferService()


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


@transfers_bp.route("", methods=["GET"])
def list_transfers():
    """
    List transfers with filters and pagination.

    Query Parameters:
        account_id (UUID): Filter by account (source or destination)
        date_from (date): Filter by start date
        date_to (date): Filter by end date
        tags (list[str]): Filter by tags (comma-separated)
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 20, max: 100)

    Returns:
        200: Paginated list of transfers
        400: Validation error
        500: Internal server error
    """
    try:
        # Parse query parameters
        filters_data = {
            "account_id": request.args.get("account_id"),
            "date_from": request.args.get("date_from"),
            "date_to": request.args.get("date_to"),
            "tags": request.args.get("tags", "").split(",") if request.args.get("tags") else None,
            "page": int(request.args.get("page", 1)),
            "limit": min(int(request.args.get("limit", 20)), 100),
        }

        # Validate filters
        filters = TransferFilters(**filters_data)

        # Get filtered transfers
        transfers, total = transfer_service.get_filtered(
            account_id=filters.account_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            tags=filters.tags,
            page=filters.page,
            limit=filters.limit,
        )

        # Format response with relations
        items = []
        for transfer in transfers:
            transfer_data = TransferResponse.model_validate(transfer).model_dump(mode="json")
            transfer_data["source_account"] = AccountResponse.model_validate(transfer.source_account).model_dump(mode="json")
            transfer_data["destination_account"] = AccountResponse.model_validate(transfer.destination_account).model_dump(mode="json")
            items.append(transfer_data)

        return paginated_response(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.limit,
        )

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except Exception as e:
        return error_response(f"Error al listar transferencias: {str(e)}", status_code=500)


@transfers_bp.route("/<uuid:transfer_id>", methods=["GET"])
def get_transfer(transfer_id: UUID):
    """
    Get a single transfer by ID.

    Path Parameters:
        transfer_id (UUID): Transfer ID

    Returns:
        200: Transfer details with relations
        404: Transfer not found
        500: Internal server error
    """
    try:
        transfer = transfer_service.get_by_id(transfer_id)

        # Format response with relations
        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        data["source_account"] = AccountResponse.model_validate(transfer.source_account).model_dump(mode="json")
        data["destination_account"] = AccountResponse.model_validate(transfer.destination_account).model_dump(mode="json")

        return success_response(data=data)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al obtener transferencia: {str(e)}", status_code=500)


@transfers_bp.route("", methods=["POST"])
def create_transfer():
    """
    Create a new transfer.

    Request Body:
        TransferCreate schema

    Returns:
        201: Created transfer
        400: Validation error
        404: Source or destination account not found
        422: Business rule violation (different currencies)
        500: Internal server error
    """
    try:
        # Validate request data
        transfer_data = TransferCreate(**request.json)

        # Create transfer (idempotent when client_id is present)
        transfer = transfer_service.create(
            source_account_id=transfer_data.source_account_id,
            destination_account_id=transfer_data.destination_account_id,
            amount=transfer_data.amount,
            date=transfer_data.date,
            description=transfer_data.description,
            tags=transfer_data.tags,
            client_id=transfer_data.client_id,
            destination_amount=transfer_data.destination_amount,
            exchange_rate=transfer_data.exchange_rate,
            base_rate=transfer_data.base_rate,
        )

        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        return success_response(
            data=data, message="Transferencia creada exitosamente", status_code=201
        )

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except ValidationError as e:
        return error_response(e.message, status_code=400)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al crear transferencia: {str(e)}", status_code=500)


@transfers_bp.route("/<uuid:transfer_id>", methods=["PUT"])
def update_transfer(transfer_id: UUID):
    """
    Update an existing transfer.

    Note: Cannot change source or destination accounts.

    Supports Last-Write-Wins (LWW) conflict detection for offline-first clients.
    When the optional request header X-Client-Updated-At is present its value is
    compared against the record's server-side updated_at timestamp.  If the
    server version is more recent the update is rejected with HTTP 409 and the
    current server state is returned so the client can reconcile.

    Path Parameters:
        transfer_id (UUID): Transfer ID

    Request Headers:
        X-Client-Updated-At (str, optional): ISO-8601 timestamp of the version
            the client last observed.  Used for LWW conflict detection.

    Request Body:
        TransferUpdate schema

    Returns:
        200: Updated transfer
        400: Validation error
        404: Transfer not found
        409: Conflict — server version is newer than client version
        500: Internal server error
    """
    try:
        # Validate request data
        transfer_data = TransferUpdate(**request.json)

        # LWW conflict detection
        client_updated_at = _parse_client_updated_at(
            request.headers.get("X-Client-Updated-At")
        )
        if client_updated_at is not None:
            current_transfer = transfer_service.get_by_id(transfer_id)
            server_updated_at = current_transfer.updated_at
            if server_updated_at.tzinfo is None:
                server_updated_at = server_updated_at.replace(tzinfo=timezone.utc)
            if server_updated_at > client_updated_at:
                server_data = TransferResponse.model_validate(current_transfer).model_dump(
                    mode="json"
                )
                return error_response(
                    "Conflicto: el servidor tiene una version mas reciente de este recurso",
                    status_code=409,
                    errors={"server_version": server_data},
                )

        # Update transfer
        transfer = transfer_service.update(
            transfer_id=transfer_id,
            amount=transfer_data.amount,
            date=transfer_data.date,
            description=transfer_data.description,
            tags=transfer_data.tags,
            destination_amount=transfer_data.destination_amount,
            exchange_rate=transfer_data.exchange_rate,
            base_rate=transfer_data.base_rate,
        )

        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        return success_response(data=data, message="Transferencia actualizada exitosamente")

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except ValidationError as e:
        return error_response(e.message, status_code=400)
    except Exception as e:
        return error_response(f"Error al actualizar transferencia: {str(e)}", status_code=500)


@transfers_bp.route("/<uuid:transfer_id>", methods=["DELETE"])
def delete_transfer(transfer_id: UUID):
    """
    Delete a transfer.

    Path Parameters:
        transfer_id (UUID): Transfer ID

    Returns:
        200: Transfer deleted successfully
        404: Transfer not found
        500: Internal server error
    """
    try:
        transfer_service.delete(transfer_id)
        return success_response(message="Transferencia eliminada exitosamente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al eliminar transferencia: {str(e)}", status_code=500)
