"""
Categories API endpoints.

All routes are protected by @require_auth. The authenticated user's UUID is
read from g.current_user_id (injected by the decorator) and forwarded to
every service call so data is always scoped to the current user.
"""

from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, make_response, request
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithSubcategories,
)
from app.services import CategoryService
from app.utils.auth import require_auth
from app.utils.exceptions import NotFoundError, BusinessRuleError
from app.utils.responses import success_response, error_response
from app.utils.sync_cursor import encode_cursor, decode_cursor

categories_bp = Blueprint("categories", __name__, url_prefix="/api/v1/categories")
category_service = CategoryService()


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


@categories_bp.route("", methods=["GET"])
@require_auth
def list_categories():
    """
    List all categories for the authenticated user.

    When the ``If-Sync-Cursor`` request header is present and valid the endpoint
    operates in incremental sync mode: only categories modified since the cursor
    timestamp are returned as a flat list.  Archived categories are always
    included in incremental mode so that deactivation changes propagate to the
    client.  If nothing has changed, 304 is returned with no body.  A fresh
    ``X-Sync-Cursor`` header is always included so the client can advance its
    cursor.

    Request Headers:
        Authorization (str): Bearer JWT token.
        If-Sync-Cursor (str, optional): Opaque cursor from a previous response.

    Query Parameters:
        type (str): Filter by category type (income, expense, both).
            Ignored in incremental mode.
        include_archived (bool): Include archived/inactive categories (default: false).
            Ignored in incremental mode (archived are always included).

    Returns:
        200: List of categories
        304: No changes since cursor (incremental mode only)
        401: Authentication required
        500: Internal server error
    """
    try:
        user_id = g.current_user_id
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()

        if updated_since is not None:
            categories = category_service.get_all(
                user_id=user_id,
                updated_since=updated_since,
                include_archived=True,
            )
            if not categories:
                resp = make_response("", 304)
                resp.headers["X-Sync-Cursor"] = new_cursor
                return resp
            data = [
                CategoryResponse.model_validate(cat).model_dump(mode="json")
                for cat in categories
            ]
            resp = make_response(jsonify({"success": True, "data": data}), 200)
            resp.headers["X-Sync-Cursor"] = new_cursor
            return resp

        type = request.args.get("type")
        include_archived = request.args.get("include_archived", "false").lower() == "true"
        categories = category_service.get_all(
            user_id=user_id, type=type, include_archived=include_archived
        )

        data = [
            CategoryResponse.model_validate(cat).model_dump(mode="json")
            for cat in categories
        ]

        body, status = success_response(data=data)
        resp = make_response(jsonify(body), status)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp

    except Exception as e:
        return error_response(f"Error al listar categorias: {str(e)}", status_code=500)


@categories_bp.route("/<uuid:category_id>", methods=["GET"])
@require_auth
def get_category(category_id: UUID):
    """
    Get a single category by ID with subcategories.

    Returns 404 if the category does not exist OR belongs to a different user.

    Path Parameters:
        category_id (UUID): Category ID

    Returns:
        200: Category details with subcategories
        401: Authentication required
        404: Category not found
        500: Internal server error
    """
    try:
        category = category_service.get_with_subcategories(
            category_id, user_id=g.current_user_id
        )

        data = CategoryResponse.model_validate(category).model_dump(mode="json")
        data["subcategories"] = [
            CategoryResponse.model_validate(sub).model_dump(mode="json")
            for sub in category.subcategories.all()
        ]

        return success_response(data=data)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al obtener categoria: {str(e)}", status_code=500)


@categories_bp.route("", methods=["POST"])
@require_auth
def create_category():
    """
    Create a new category for the authenticated user.

    Request Body:
        CategoryCreate schema

    Returns:
        201: Created category
        400: Validation error
        401: Authentication required
        404: Parent category not found
        422: Business rule violation
        500: Internal server error
    """
    try:
        category_data = CategoryCreate(**request.json)

        category = category_service.create(
            user_id=g.current_user_id,
            name=category_data.name,
            type=category_data.type.value,
            icon=category_data.icon,
            color=category_data.color,
            parent_category_id=category_data.parent_category_id,
            client_id=category_data.client_id,
        )

        data = CategoryResponse.model_validate(category).model_dump(mode="json")
        return success_response(
            data=data, message="Categoria creada exitosamente", status_code=201
        )

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al crear categoria: {str(e)}", status_code=500)


@categories_bp.route("/<uuid:category_id>", methods=["PUT"])
@require_auth
def update_category(category_id: UUID):
    """
    Update an existing category for the authenticated user.

    Supports Last-Write-Wins (LWW) conflict detection for offline-first clients.
    When the optional request header X-Client-Updated-At is present its value is
    compared against the record's server-side updated_at timestamp.  If the
    server version is more recent the update is rejected with HTTP 409.

    Path Parameters:
        category_id (UUID): Category ID

    Request Headers:
        Authorization (str): Bearer JWT token.
        X-Client-Updated-At (str, optional): ISO-8601 timestamp of the version
            the client last observed.  Used for LWW conflict detection.

    Request Body:
        CategoryUpdate schema

    Returns:
        200: Updated category
        400: Validation error
        401: Authentication required
        404: Category not found
        409: Conflict — server version is newer than client version
        422: Business rule violation
        500: Internal server error
    """
    try:
        category_data = CategoryUpdate(**request.json)
        user_id = g.current_user_id

        client_updated_at = _parse_client_updated_at(
            request.headers.get("X-Client-Updated-At")
        )
        if client_updated_at is not None:
            current_category = category_service.get_by_id(
                category_id, user_id=user_id
            )
            server_updated_at = current_category.updated_at
            if server_updated_at.tzinfo is None:
                server_updated_at = server_updated_at.replace(tzinfo=timezone.utc)
            if server_updated_at > client_updated_at:
                server_data = CategoryResponse.model_validate(
                    current_category
                ).model_dump(mode="json")
                return error_response(
                    "Conflicto: el servidor tiene una version mas reciente de este recurso",
                    status_code=409,
                    errors={"server_version": server_data},
                )

        category = category_service.update(
            category_id=category_id,
            user_id=user_id,
            name=category_data.name,
            type=category_data.type.value if category_data.type else None,
            icon=category_data.icon,
            color=category_data.color,
            parent_category_id=category_data.parent_category_id,
            active=category_data.active,
        )

        data = CategoryResponse.model_validate(category).model_dump(mode="json")
        return success_response(data=data, message="Categoria actualizada exitosamente")

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=e.errors())
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al actualizar categoria: {str(e)}", status_code=500)


@categories_bp.route("/<uuid:category_id>", methods=["DELETE"])
@require_auth
def delete_category(category_id: UUID):
    """
    Archive a category (soft delete — sets active to False).

    Path Parameters:
        category_id (UUID): Category ID

    Returns:
        200: Category archived successfully
        401: Authentication required
        404: Category not found
        422: Business rule violation
        500: Internal server error
    """
    try:
        category_service.archive(category_id, user_id=g.current_user_id)
        return success_response(message="Categoría archivada exitosamente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al archivar categoria: {str(e)}", status_code=500)


@categories_bp.route("/<uuid:category_id>/permanent", methods=["DELETE"])
@require_auth
def hard_delete_category(category_id: UUID):
    """
    Permanently delete a category (hard delete — irreversible).

    Path Parameters:
        category_id (UUID): Category ID

    Returns:
        200: Category permanently deleted
        401: Authentication required
        404: Category not found
        422: Category has subcategories or transactions
        500: Internal server error
    """
    try:
        category_service.hard_delete(category_id, user_id=g.current_user_id)
        return success_response(message="Categoría eliminada permanentemente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al eliminar categoria: {str(e)}", status_code=500)
