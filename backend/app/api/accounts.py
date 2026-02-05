"""
Accounts API endpoints.
"""

from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountWithBalance,
)
from app.services import AccountService
from app.utils.exceptions import NotFoundError, ValidationError, BusinessRuleError
from app.utils.responses import success_response, error_response

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/v1/accounts")
account_service = AccountService()


@accounts_bp.route("", methods=["GET"])
def list_accounts():
    """
    List all accounts.

    Query Parameters:
        include_archived (bool): Include inactive accounts (default: false)

    Returns:
        200: List of accounts with balances
        500: Internal server error
    """
    try:
        include_archived = request.args.get("include_archived", "false").lower() == "true"

        accounts_with_balances = account_service.get_all_with_balances(
            include_archived=include_archived
        )

        # Format response with balances
        data = [
            {
                **AccountResponse.model_validate(account).model_dump(mode="json"),
                "balance": str(balance),
            }
            for account, balance in accounts_with_balances
        ]

        return success_response(data=data)

    except Exception as e:
        return error_response(f"Error al listar cuentas: {str(e)}", status_code=500)


@accounts_bp.route("/<uuid:account_id>", methods=["GET"])
def get_account(account_id: UUID):
    """
    Get a single account by ID.

    Path Parameters:
        account_id (UUID): Account ID

    Returns:
        200: Account details with balance
        404: Account not found
        500: Internal server error
    """
    try:
        account, balance = account_service.get_with_balance(account_id)

        data = {
            **AccountResponse.model_validate(account).model_dump(mode="json"),
            "balance": str(balance),
        }

        return success_response(data=data)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al obtener cuenta: {str(e)}", status_code=500)


@accounts_bp.route("", methods=["POST"])
def create_account():
    """
    Create a new account.

    Request Body:
        AccountCreate schema

    Returns:
        201: Created account
        400: Validation error
        500: Internal server error
    """
    try:
        # Validate request data
        account_data = AccountCreate(**request.json)

        # Create account
        account = account_service.create(
            nombre=account_data.nombre,
            tipo=account_data.tipo.value,
            divisa=account_data.divisa,
            descripcion=account_data.descripcion,
            tags=account_data.tags,
        )

        data = AccountResponse.model_validate(account).model_dump(mode="json")
        return success_response(data=data, message="Cuenta creada exitosamente", status_code=201)

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except ValueError as e:
        return error_response(str(e), status_code=400)
    except BusinessRuleError as e:
        return error_response(str(e), status_code=400)
    except NotFoundError as e:
        return error_response(str(e), status_code=404)
    except Exception as e:
        return error_response(f"Error al crear cuenta: {str(e)}", status_code=500)


@accounts_bp.route("/<uuid:account_id>", methods=["PUT"])
def update_account(account_id: UUID):
    """
    Update an existing account.

    Path Parameters:
        account_id (UUID): Account ID

    Request Body:
        AccountUpdate schema

    Returns:
        200: Updated account
        400: Validation error
        404: Account not found
        500: Internal server error
    """
    try:
        # Validate request data
        account_data = AccountUpdate(**request.json)

        # Update account
        account = account_service.update(
            account_id=account_id,
            nombre=account_data.nombre,
            tipo=account_data.tipo.value if account_data.tipo else None,
            divisa=account_data.divisa,
            descripcion=account_data.descripcion,
            tags=account_data.tags,
            activa=account_data.activa,
        )

        data = AccountResponse.model_validate(account).model_dump(mode="json")
        return success_response(data=data, message="Cuenta actualizada exitosamente")

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al actualizar cuenta: {str(e)}", status_code=500)


@accounts_bp.route("/<uuid:account_id>", methods=["DELETE"])
def delete_account(account_id: UUID):
    """
    Archive an account (soft delete).

    Path Parameters:
        account_id (UUID): Account ID

    Returns:
        200: Account archived successfully
        404: Account not found
        422: Account has transactions/transfers
        500: Internal server error
    """
    try:
        account_service.archive(account_id)
        return success_response(message="Cuenta archivada exitosamente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al archivar cuenta: {str(e)}", status_code=500)


@accounts_bp.route("/<uuid:account_id>/balance", methods=["GET"])
def get_account_balance(account_id: UUID):
    """
    Get calculated balance for an account.

    Path Parameters:
        account_id (UUID): Account ID

    Returns:
        200: Account balance
        404: Account not found
        500: Internal server error
    """
    try:
        balance = account_service.get_balance(account_id)

        return success_response(
            data={
                "account_id": str(account_id),
                "balance": str(balance),
            }
        )

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al calcular balance: {str(e)}", status_code=500)
