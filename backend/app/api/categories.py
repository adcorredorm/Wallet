"""
Categories API endpoints.
"""

from datetime import datetime, timezone
from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithSubcategories,
)
from app.services import CategoryService
from app.utils.exceptions import NotFoundError, BusinessRuleError
from app.utils.responses import success_response, error_response

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
def list_categories():
    """
    List all categories.

    Query Parameters:
        tipo (str): Filter by category type (ingreso, gasto, ambos)

    Returns:
        200: List of categories
        500: Internal server error
    """
    try:
        tipo = request.args.get("tipo")
        categories = category_service.get_all(tipo=tipo)

        data = [
            CategoryResponse.model_validate(cat).model_dump(mode="json")
            for cat in categories
        ]

        return success_response(data=data)

    except Exception as e:
        return error_response(f"Error al listar categorias: {str(e)}", status_code=500)


@categories_bp.route("/<uuid:category_id>", methods=["GET"])
def get_category(category_id: UUID):
    """
    Get a single category by ID with subcategories.

    Path Parameters:
        category_id (UUID): Category ID

    Returns:
        200: Category details with subcategories
        404: Category not found
        500: Internal server error
    """
    try:
        category = category_service.get_with_subcategories(category_id)

        # Format with subcategories
        data = CategoryResponse.model_validate(category).model_dump(mode="json")
        data["subcategorias"] = [
            CategoryResponse.model_validate(sub).model_dump(mode="json")
            for sub in category.subcategorias.all()
        ]

        return success_response(data=data)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al obtener categoria: {str(e)}", status_code=500)


@categories_bp.route("", methods=["POST"])
def create_category():
    """
    Create a new category.

    Request Body:
        CategoryCreate schema

    Returns:
        201: Created category
        400: Validation error
        404: Parent category not found
        422: Business rule violation
        500: Internal server error
    """
    try:
        # Validate request data
        category_data = CategoryCreate(**request.json)

        # Create category (idempotent when client_id is present)
        category = category_service.create(
            nombre=category_data.nombre,
            tipo=category_data.tipo.value,
            icono=category_data.icono,
            color=category_data.color,
            categoria_padre_id=category_data.categoria_padre_id,
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
def update_category(category_id: UUID):
    """
    Update an existing category.

    Supports Last-Write-Wins (LWW) conflict detection for offline-first clients.
    When the optional request header X-Client-Updated-At is present its value is
    compared against the record's server-side updated_at timestamp.  If the
    server version is more recent the update is rejected with HTTP 409 and the
    current server state is returned so the client can reconcile.

    Path Parameters:
        category_id (UUID): Category ID

    Request Headers:
        X-Client-Updated-At (str, optional): ISO-8601 timestamp of the version
            the client last observed.  Used for LWW conflict detection.

    Request Body:
        CategoryUpdate schema

    Returns:
        200: Updated category
        400: Validation error
        404: Category not found
        409: Conflict — server version is newer than client version
        422: Business rule violation
        500: Internal server error
    """
    try:
        # Validate request data
        category_data = CategoryUpdate(**request.json)

        # LWW conflict detection
        client_updated_at = _parse_client_updated_at(
            request.headers.get("X-Client-Updated-At")
        )
        if client_updated_at is not None:
            current_category = category_service.get_by_id(category_id)
            server_updated_at = current_category.updated_at
            if server_updated_at.tzinfo is None:
                server_updated_at = server_updated_at.replace(tzinfo=timezone.utc)
            if server_updated_at > client_updated_at:
                server_data = CategoryResponse.model_validate(current_category).model_dump(
                    mode="json"
                )
                return error_response(
                    "Conflicto: el servidor tiene una version mas reciente de este recurso",
                    status_code=409,
                    errors={"server_version": server_data},
                )

        # Update category
        category = category_service.update(
            category_id=category_id,
            nombre=category_data.nombre,
            tipo=category_data.tipo.value if category_data.tipo else None,
            icono=category_data.icono,
            color=category_data.color,
            categoria_padre_id=category_data.categoria_padre_id,
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
def delete_category(category_id: UUID):
    """
    Delete a category.

    Path Parameters:
        category_id (UUID): Category ID

    Returns:
        200: Category deleted successfully
        404: Category not found
        422: Category has subcategories or transactions
        500: Internal server error
    """
    try:
        category_service.delete(category_id)
        return success_response(message="Categoria eliminada exitosamente")

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except BusinessRuleError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(f"Error al eliminar categoria: {str(e)}", status_code=500)
