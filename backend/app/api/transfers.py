"""
Transfers API endpoints.
"""

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
from app.utils.exceptions import NotFoundError, BusinessRuleError
from app.utils.responses import success_response, error_response, paginated_response

transfers_bp = Blueprint("transfers", __name__, url_prefix="/api/v1/transfers")
transfer_service = TransferService()


@transfers_bp.route("", methods=["GET"])
def list_transfers():
    """
    List transfers with filters and pagination.

    Query Parameters:
        cuenta_id (UUID): Filter by account (source or destination)
        fecha_desde (date): Filter by start date
        fecha_hasta (date): Filter by end date
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
            "cuenta_id": request.args.get("cuenta_id"),
            "fecha_desde": request.args.get("fecha_desde"),
            "fecha_hasta": request.args.get("fecha_hasta"),
            "tags": request.args.get("tags", "").split(",") if request.args.get("tags") else None,
            "page": int(request.args.get("page", 1)),
            "limit": min(int(request.args.get("limit", 20)), 100),
        }

        # Validate filters
        filters = TransferFilters(**filters_data)

        # Get filtered transfers
        transfers, total = transfer_service.get_filtered(
            cuenta_id=filters.cuenta_id,
            fecha_desde=filters.fecha_desde,
            fecha_hasta=filters.fecha_hasta,
            tags=filters.tags,
            page=filters.page,
            limit=filters.limit,
        )

        # Format response with relations
        items = []
        for transfer in transfers:
            transfer_data = TransferResponse.model_validate(transfer).model_dump(mode="json")
            transfer_data["cuenta_origen"] = AccountResponse.model_validate(transfer.cuenta_origen).model_dump(mode="json")
            transfer_data["cuenta_destino"] = AccountResponse.model_validate(transfer.cuenta_destino).model_dump(mode="json")
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
        data["cuenta_origen"] = AccountResponse.model_validate(transfer.cuenta_origen).model_dump(mode="json")
        data["cuenta_destino"] = AccountResponse.model_validate(transfer.cuenta_destino).model_dump(mode="json")

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

        # Create transfer
        transfer = transfer_service.create(
            cuenta_origen_id=transfer_data.cuenta_origen_id,
            cuenta_destino_id=transfer_data.cuenta_destino_id,
            monto=transfer_data.monto,
            fecha=transfer_data.fecha,
            descripcion=transfer_data.descripcion,
            tags=transfer_data.tags,
        )

        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        return success_response(
            data=data, message="Transferencia creada exitosamente", status_code=201
        )

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al crear transferencia: {str(e)}", status_code=500)


@transfers_bp.route("/<uuid:transfer_id>", methods=["PUT"])
def update_transfer(transfer_id: UUID):
    """
    Update an existing transfer.

    Note: Cannot change source or destination accounts.

    Path Parameters:
        transfer_id (UUID): Transfer ID

    Request Body:
        TransferUpdate schema

    Returns:
        200: Updated transfer
        400: Validation error
        404: Transfer not found
        500: Internal server error
    """
    try:
        # Validate request data
        transfer_data = TransferUpdate(**request.json)

        # Update transfer
        transfer = transfer_service.update(
            transfer_id=transfer_id,
            monto=transfer_data.monto,
            fecha=transfer_data.fecha,
            descripcion=transfer_data.descripcion,
            tags=transfer_data.tags,
        )

        data = TransferResponse.model_validate(transfer).model_dump(mode="json")
        return success_response(data=data, message="Transferencia actualizada exitosamente")

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
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
