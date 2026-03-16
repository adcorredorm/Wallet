"""
Accounts API endpoints.

All routes are protected by @require_auth. The authenticated user's UUID is
read from g.current_user_id (injected by the decorator) and forwarded to
every service call so data is always scoped to the current user.
"""

from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, make_response, request
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
)
from app.services import AccountService
from app.utils.auth import require_auth
from app.utils.exceptions import NotFoundError, ValidationError, BusinessRuleError
from app.utils.responses import success_response, error_response
from app.utils.sync_cursor import encode_cursor, decode_cursor

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/v1/accounts")
account_service = AccountService()


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


@accounts_bp.route("", methods=["GET"])
@require_auth
def list_accounts():
    """
    List all accounts for the authenticated user.

    When the ``If-Sync-Cursor`` request header is present and valid the endpoint
    operates in incremental sync mode: only accounts modified since the cursor
    timestamp are returned as a flat list.  If nothing has changed, 304 is
    returned with no body.  A fresh ``X-Sync-Cursor`` header is always included
    in the response so the client can advance its cursor.

    Balance is intentionally omitted from all responses — it is computed
    locally by the frontend from Dexie transaction data.

    Request Headers:
        Authorization (str): Bearer JWT token.
        If-Sync-Cursor (str, optional): Opaque cursor from a previous response.

    Query Parameters:
        include_archived (bool): Include inactive accounts (default: false).
            Ignored in incremental mode (archived accounts are always included
            so that deletions propagate to the client).

    Returns:
        200: List of accounts (full sync or incremental with changes)
        304: No changes since cursor (incremental mode only)
        401: Authentication required
        500: Internal server error
    """
    try:
        user_id = g.current_user_id
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()

        if updated_since is not None:
            accounts = account_service.get_all(
                user_id=user_id, include_archived=True, updated_since=updated_since
            )
            if not accounts:
                resp = make_response("", 304)
                resp.headers["X-Sync-Cursor"] = new_cursor
                return resp
            data = [
                AccountResponse.model_validate(account).model_dump(mode="json")
                for account in accounts
            ]
            resp = make_response(jsonify({"success": True, "data": data}), 200)
            resp.headers["X-Sync-Cursor"] = new_cursor
            return resp

        include_archived = request.args.get("include_archived", "false").lower() == "true"

        accounts = account_service.get_all(
            user_id=user_id, include_archived=include_archived
        )

        data = [
            AccountResponse.model_validate(account).model_dump(mode="json")
            for account in accounts
        ]

        body, status = success_response(data=data)
        resp = make_response(jsonify(body), status)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp

    except Exception as e:
        return error_response(f"Error al listar cuentas: {str(e)}", status_code=500)


@accounts_bp.route("/<uuid:account_id>", methods=["GET"])
@require_auth
def get_account(account_id: UUID):
    """
    Get a single account by ID for the authenticated user.

    Returns 404 if the account does not exist OR belongs to a different user
    (ownership is enforced silently — the record simply isn't found).

    Balance is intentionally omitted — it is computed locally by the frontend.

    Path Parameters:
        account_id (UUID): Account ID

    Returns:
        200: Account details
        401: Authentication required
        404: Account not found
        500: Internal server error
    """
    try:
        account = account_service.get_by_id(account_id, user_id=g.current_user_id)
        data = AccountResponse.model_validate(account).model_dump(mode="json")
        return success_response(data=data)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al obtener cuenta: {str(e)}", status_code=500)


@accounts_bp.route("", methods=["POST"])
@require_auth
def create_account():
    """
    Create a new account for the authenticated user.

    Request Body:
        AccountCreate schema

    Returns:
        201: Created account
        400: Validation error
        401: Authentication required
        500: Internal server error
    """
    try:
        account_data = AccountCreate(**request.json)

        account = account_service.create(
            user_id=g.current_user_id,
            name=account_data.name,
            type=account_data.type.value,
            currency=account_data.currency,
            description=account_data.description,
            tags=account_data.tags,
            client_id=account_data.client_id,
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
@require_auth
def update_account(account_id: UUID):
    """
    Update an existing account for the authenticated user.

    Supports Last-Write-Wins (LWW) conflict detection for offline-first clients.
    When the optional request header X-Client-Updated-At is present its value is
    compared against the record's server-side updated_at timestamp.  If the
    server version is more recent the update is rejected with HTTP 409 and the
    current server state is returned so the client can reconcile.

    Path Parameters:
        account_id (UUID): Account ID

    Request Headers:
        Authorization (str): Bearer JWT token.
        X-Client-Updated-At (str, optional): ISO-8601 timestamp of the version
            the client last observed.  Used for LWW conflict detection.

    Request Body:
        AccountUpdate schema

    Returns:
        200: Updated account
        400: Validation error
        401: Authentication required
        404: Account not found
        409: Conflict — server version is newer than client version
        500: Internal server error
    """
    try:
        account_data = AccountUpdate(**request.json)
        user_id = g.current_user_id

        client_updated_at = _parse_client_updated_at(
            request.headers.get("X-Client-Updated-At")
        )
        if client_updated_at is not None:
            current_account = account_service.get_by_id(account_id, user_id=user_id)
            server_updated_at = current_account.updated_at
            if server_updated_at.tzinfo is None:
                server_updated_at = server_updated_at.replace(tzinfo=timezone.utc)
            if server_updated_at > client_updated_at:
                server_data = AccountResponse.model_validate(current_account).model_dump(
                    mode="json"
                )
                return error_response(
                    "Conflicto: el servidor tiene una version mas reciente de este recurso",
                    status_code=409,
                    errors={"server_version": server_data},
                )

        account = account_service.update(
            account_id=account_id,
            user_id=user_id,
            name=account_data.name,
            type=account_data.type.value if account_data.type else None,
            currency=account_data.currency,
            description=account_data.description,
            tags=account_data.tags,
            active=account_data.active,
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
@require_auth
def delete_account(account_id: UUID):
    """
    Archive an account (soft delete) for the authenticated user.

    Path Parameters:
        account_id (UUID): Account ID

    Returns:
        200: Account archived successfully
        401: Authentication required
        404: Account not found
        422: Account has transactions/transfers
        500: Internal server error
    """
    try:
        account_service.archive(account_id, user_id=g.current_user_id)
        return success_response(message="Cuenta archivada exitosamente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al archivar cuenta: {str(e)}", status_code=500)


@accounts_bp.route("/<uuid:account_id>/permanent", methods=["DELETE"])
@require_auth
def hard_delete_account(account_id: UUID):
    """
    Permanently delete an account (hard delete — irreversible).

    Only succeeds if the account has no transactions or transfers.

    Path Parameters:
        account_id (UUID): Account ID

    Returns:
        200: Account permanently deleted
        401: Authentication required
        404: Account not found
        422: Account has transactions or transfers
        500: Internal server error
    """
    try:
        account_service.delete(account_id, user_id=g.current_user_id)
        return success_response(message="Cuenta eliminada permanentemente")
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al eliminar cuenta: {str(e)}", status_code=500)


