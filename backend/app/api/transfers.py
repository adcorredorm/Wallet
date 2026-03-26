"""
Transfers API endpoints.

All routes are protected by @require_auth. The authenticated user's UUID is
read from g.current_user_id (injected by the decorator) and forwarded to
every service call so data is always scoped to the current user.
"""

from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, make_response, request
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
from app.utils.auth import require_auth
from app.utils.exceptions import NotFoundError, BusinessRuleError, ValidationError
from app.utils.responses import success_response, error_response, serialize_pydantic_errors, paginated_response
from app.utils.sync_cursor import encode_cursor, decode_cursor

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
@require_auth
def list_transfers():
    """
    List transfers with filters and pagination for the authenticated user.

    When the ``If-Sync-Cursor`` request header is present and valid the endpoint
    operates in incremental sync mode: only transfers modified since the cursor
    timestamp are returned as a flat list (bypassing pagination).  If nothing has
    changed, 304 is returned with no body.  A fresh ``X-Sync-Cursor`` header is
    always included so the client can advance its cursor.

    Request Headers:
        Authorization (str): Bearer JWT token.
        If-Sync-Cursor (str, optional): Opaque cursor from a previous response.

    Query Parameters:
        account_id (UUID): Filter by account (source or destination)
        date_from (date): Filter by start date
        date_to (date): Filter by end date
        tags (list[str]): Filter by tags (comma-separated)
        page (int): Page number (default: 1, ignored in incremental mode)
        limit (int): Items per page (default: 20, max: 10000, ignored in incremental mode)

    Returns:
        200: Paginated list of transfers (full sync) or flat list (incremental)
        304: No changes since cursor (incremental mode only)
        400: Validation error
        401: Authentication required
        500: Internal server error
    """
    try:
        user_id = g.current_user_id
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()

        if updated_since is not None:
            transfers, _ = transfer_service.get_filtered(
                user_id=user_id,
                updated_since=updated_since,
                limit=10000,
                page=1,
            )
            if not transfers:
                resp = make_response("", 304)
                resp.headers["X-Sync-Cursor"] = new_cursor
                return resp
            data = [
                TransferResponse.model_validate(t).model_dump(mode="json")
                for t in transfers
            ]
            resp = make_response(jsonify({"success": True, "data": data}), 200)
            resp.headers["X-Sync-Cursor"] = new_cursor
            return resp

        filters_data = {
            "account_id": request.args.get("account_id"),
            "date_from": request.args.get("date_from"),
            "date_to": request.args.get("date_to"),
            "tags": request.args.get("tags", "").split(",") if request.args.get("tags") else None,
            "page": int(request.args.get("page", 1)),
            "limit": min(int(request.args.get("limit", 20)), 10000),
        }

        filters = TransferFilters(**filters_data)

        transfers, total = transfer_service.get_filtered(
            user_id=user_id,
            account_id=filters.account_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            tags=filters.tags,
            page=filters.page,
            limit=filters.limit,
        )

        items = []
        for transfer in transfers:
            transfer_data = TransferResponse.model_validate(transfer).model_dump(mode="json")
            transfer_data["source_account"] = AccountResponse.model_validate(
                transfer.source_account
            ).model_dump(mode="json")
            transfer_data["destination_account"] = AccountResponse.model_validate(
                transfer.destination_account
            ).model_dump(mode="json")
            items.append(transfer_data)

        body, status = paginated_response(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.limit,
        )
        resp = make_response(jsonify(body), status)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=serialize_pydantic_errors(e.errors()))
    except Exception as e:
        return error_response(f"Error al listar transferencias: {str(e)}", status_code=500)


@transfers_bp.route("/<uuid:transfer_id>", methods=["GET"])
@require_auth
def get_transfer(transfer_id: UUID):
    """
    Get a single transfer by ID for the authenticated user.

    Returns 404 if the transfer does not exist OR belongs to a different user.

    Path Parameters:
        transfer_id (UUID): Transfer ID

    Returns:
        200: Transfer details with relations
        401: Authentication required
        404: Transfer not found
        500: Internal server error
    """
    try:
        transfer = transfer_service.get_by_id(transfer_id, user_id=g.current_user_id)

        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        data["source_account"] = AccountResponse.model_validate(
            transfer.source_account
        ).model_dump(mode="json")
        data["destination_account"] = AccountResponse.model_validate(
            transfer.destination_account
        ).model_dump(mode="json")

        return success_response(data=data)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al obtener transferencia: {str(e)}", status_code=500)


@transfers_bp.route("", methods=["POST"])
@require_auth
def create_transfer():
    """
    Create a new transfer for the authenticated user.

    Request Body:
        TransferCreate schema

    Returns:
        201: Created transfer
        400: Validation error
        401: Authentication required
        404: Source or destination account not found
        422: Business rule violation
        500: Internal server error
    """
    try:
        transfer_data = TransferCreate(**request.json)

        transfer = transfer_service.create(
            user_id=g.current_user_id,
            source_account_id=transfer_data.source_account_id,
            destination_account_id=transfer_data.destination_account_id,
            amount=transfer_data.amount,
            date=transfer_data.date,
            title=transfer_data.title,
            description=transfer_data.description,
            tags=transfer_data.tags,
            offline_id=transfer_data.offline_id,
            destination_amount=transfer_data.destination_amount,
            exchange_rate=transfer_data.exchange_rate,
            base_rate=transfer_data.base_rate,
        )

        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        return success_response(
            data=data, message="Transferencia creada exitosamente", status_code=201
        )

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=serialize_pydantic_errors(e.errors()))
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except ValidationError as e:
        return error_response(e.message, status_code=400)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al crear transferencia: {str(e)}", status_code=500)


@transfers_bp.route("/<uuid:transfer_id>", methods=["PUT"])
@require_auth
def update_transfer(transfer_id: UUID):
    """
    Update an existing transfer for the authenticated user.

    Note: Cannot change source or destination accounts.

    Supports Last-Write-Wins (LWW) conflict detection for offline-first clients.
    When the optional request header X-Client-Updated-At is present its value is
    compared against the record's server-side updated_at timestamp.  If the
    server version is more recent the update is rejected with HTTP 409.

    Path Parameters:
        transfer_id (UUID): Transfer ID

    Request Headers:
        Authorization (str): Bearer JWT token.
        X-Client-Updated-At (str, optional): ISO-8601 timestamp of the version
            the client last observed.  Used for LWW conflict detection.

    Request Body:
        TransferUpdate schema

    Returns:
        200: Updated transfer
        400: Validation error
        401: Authentication required
        404: Transfer not found
        409: Conflict — server version is newer than client version
        500: Internal server error
    """
    try:
        transfer_data = TransferUpdate(**request.json)
        user_id = g.current_user_id

        client_updated_at = _parse_client_updated_at(
            request.headers.get("X-Client-Updated-At")
        )
        if client_updated_at is not None:
            current_transfer = transfer_service.get_by_id(transfer_id, user_id=user_id)
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

        transfer = transfer_service.update(
            transfer_id=transfer_id,
            user_id=user_id,
            amount=transfer_data.amount,
            date=transfer_data.date,
            title=transfer_data.title,
            description=transfer_data.description,
            tags=transfer_data.tags,
            destination_amount=transfer_data.destination_amount,
            exchange_rate=transfer_data.exchange_rate,
            base_rate=transfer_data.base_rate,
        )

        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        return success_response(data=data, message="Transferencia actualizada exitosamente")

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=serialize_pydantic_errors(e.errors()))
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except ValidationError as e:
        return error_response(e.message, status_code=400)
    except Exception as e:
        return error_response(f"Error al actualizar transferencia: {str(e)}", status_code=500)


@transfers_bp.route("/<uuid:transfer_id>", methods=["DELETE"])
@require_auth
def delete_transfer(transfer_id: UUID):
    """
    Delete a transfer for the authenticated user.

    Path Parameters:
        transfer_id (UUID): Transfer ID

    Returns:
        200: Transfer deleted successfully
        401: Authentication required
        404: Transfer not found
        500: Internal server error
    """
    try:
        transfer_service.delete(transfer_id, user_id=g.current_user_id)
        return success_response(message="Transferencia eliminada exitosamente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al eliminar transferencia: {str(e)}", status_code=500)
