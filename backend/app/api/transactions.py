"""
Transactions API endpoints.
"""

from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID
from datetime import date

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


@transactions_bp.route("", methods=["GET"])
def list_transactions():
    """
    List transactions with filters and pagination.

    Query Parameters:
        cuenta_id (UUID): Filter by account
        categoria_id (UUID): Filter by category
        tipo (str): Filter by type (ingreso, gasto)
        fecha_desde (date): Filter by start date
        fecha_hasta (date): Filter by end date
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
            "cuenta_id": request.args.get("cuenta_id"),
            "categoria_id": request.args.get("categoria_id"),
            "tipo": request.args.get("tipo"),
            "fecha_desde": request.args.get("fecha_desde"),
            "fecha_hasta": request.args.get("fecha_hasta"),
            "tags": request.args.get("tags", "").split(",") if request.args.get("tags") else None,
            "page": int(request.args.get("page", 1)),
            "limit": min(int(request.args.get("limit", 20)), 100),
        }

        # Validate filters
        filters = TransactionFilters(**filters_data)

        # Get filtered transactions
        transactions, total = transaction_service.get_filtered(
            cuenta_id=filters.cuenta_id,
            categoria_id=filters.categoria_id,
            tipo=filters.tipo.value if filters.tipo else None,
            fecha_desde=filters.fecha_desde,
            fecha_hasta=filters.fecha_hasta,
            tags=filters.tags,
            page=filters.page,
            limit=filters.limit,
        )

        # Format response with relations
        items = []
        for trans in transactions:
            trans_data = TransactionResponse.model_validate(trans).model_dump(mode="json")
            trans_data["cuenta"] = AccountResponse.model_validate(trans.cuenta).model_dump(mode="json")
            trans_data["categoria"] = CategoryResponse.model_validate(trans.categoria).model_dump(mode="json")
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
        data["cuenta"] = AccountResponse.model_validate(transaction.cuenta).model_dump(mode="json")
        data["categoria"] = CategoryResponse.model_validate(transaction.categoria).model_dump(mode="json")

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

        # Create transaction
        transaction = transaction_service.create(
            tipo=transaction_data.tipo.value,
            monto=transaction_data.monto,
            fecha=transaction_data.fecha,
            cuenta_id=transaction_data.cuenta_id,
            categoria_id=transaction_data.categoria_id,
            titulo=transaction_data.titulo,
            descripcion=transaction_data.descripcion,
            tags=transaction_data.tags,
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

    Path Parameters:
        transaction_id (UUID): Transaction ID

    Request Body:
        TransactionUpdate schema

    Returns:
        200: Updated transaction
        400: Validation error
        404: Transaction, account, or category not found
        422: Business rule violation
        500: Internal server error
    """
    try:
        # Validate request data
        transaction_data = TransactionUpdate(**request.json)

        # Update transaction
        transaction = transaction_service.update(
            transaction_id=transaction_id,
            tipo=transaction_data.tipo.value if transaction_data.tipo else None,
            monto=transaction_data.monto,
            fecha=transaction_data.fecha,
            cuenta_id=transaction_data.cuenta_id,
            categoria_id=transaction_data.categoria_id,
            titulo=transaction_data.titulo,
            descripcion=transaction_data.descripcion,
            tags=transaction_data.tags,
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
