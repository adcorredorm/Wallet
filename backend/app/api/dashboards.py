"""
Dashboards blueprint — CRUD for user-defined analytics dashboards.

All routes are protected by @require_auth. The authenticated user's UUID is
read from g.current_user_id (injected by the decorator) and forwarded to
every service call so data is always scoped to the current user.

Endpoints:
  GET    /api/v1/dashboards
  POST   /api/v1/dashboards
  GET    /api/v1/dashboards/<dashboard_id>
  PUT    /api/v1/dashboards/<dashboard_id>
  DELETE /api/v1/dashboards/<dashboard_id>
  POST   /api/v1/dashboards/<dashboard_id>/widgets
  PUT    /api/v1/dashboards/<dashboard_id>/widgets/<widget_id>
  DELETE /api/v1/dashboards/<dashboard_id>/widgets/<widget_id>
"""

from uuid import UUID

from flask import Blueprint, g, jsonify, make_response, request
from pydantic import ValidationError

from app.services.dashboard_crud import DashboardCrudService
from app.schemas.dashboard_crud import (
    DashboardCreate,
    DashboardUpdate,
    DashboardResponse,
    DashboardWithWidgetsResponse,
    WidgetCreate,
    WidgetUpdate,
    WidgetResponse,
)
from app.utils.auth import require_auth
from app.utils.responses import success_response, error_response, serialize_pydantic_errors
from app.utils.exceptions import WalletException
from app.utils.sync_cursor import encode_cursor, decode_cursor

dashboards_bp = Blueprint("dashboards", __name__, url_prefix="/api/v1/dashboards")
_service = DashboardCrudService()


def _serialize_dashboard(dashboard) -> dict:
    return DashboardResponse.model_validate(dashboard).model_dump(mode="json")


def _serialize_dashboard_with_widgets(dashboard, widgets) -> dict:
    data = DashboardWithWidgetsResponse.model_validate(dashboard)
    data.widgets = [WidgetResponse.model_validate(w) for w in widgets]
    return data.model_dump(mode="json")


def _serialize_widget(widget) -> dict:
    return WidgetResponse.model_validate(widget).model_dump(mode="json")


@dashboards_bp.route("", methods=["GET"])
@require_auth
def list_dashboards():
    """
    List all dashboards for the authenticated user.

    When the ``If-Sync-Cursor`` request header is present and valid the endpoint
    operates in incremental sync mode: only dashboards modified since the cursor
    timestamp are returned as a flat list.  If nothing has changed, 304 is
    returned with no body.  A fresh ``X-Sync-Cursor`` header is always included
    so the client can advance its cursor.

    Request Headers:
        Authorization (str): Bearer JWT token.
        If-Sync-Cursor (str, optional): Opaque cursor from a previous response.

    Returns:
        200: List of dashboards
        304: No changes since cursor (incremental mode only)
        401: Authentication required
        500: Internal server error
    """
    try:
        user_id = g.current_user_id
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()

        if updated_since is not None:
            dashboards = _service.list_dashboards(
                user_id=user_id, updated_since=updated_since
            )
            if not dashboards:
                resp = make_response("", 304)
                resp.headers["X-Sync-Cursor"] = new_cursor
                return resp
            data = [_serialize_dashboard(d) for d in dashboards]
            resp = make_response(jsonify({"success": True, "data": data}), 200)
            resp.headers["X-Sync-Cursor"] = new_cursor
            return resp

        dashboards = _service.list_dashboards(user_id=user_id)
        body, status = success_response(data=[_serialize_dashboard(d) for d in dashboards])
        resp = make_response(jsonify(body), status)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp
    except Exception as exc:
        return error_response(f"Error al listar dashboards: {exc}", status_code=500)


@dashboards_bp.route("", methods=["POST"])
@require_auth
def create_dashboard():
    """
    Create a new dashboard for the authenticated user.

    Request Body:
        DashboardCreate schema

    Returns:
        201: Dashboard created (or 200 if idempotent duplicate)
        400: Validation error
        401: Authentication required
        500: Internal server error
    """
    try:
        body = DashboardCreate.model_validate(request.get_json(force=True) or {})
        dashboard, created = _service.create_dashboard(user_id=g.current_user_id, data=body)
        status = 201 if created else 200
        return success_response(data=_serialize_dashboard(dashboard), status_code=status)
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=serialize_pydantic_errors(exc.errors()))
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al crear dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>", methods=["GET"])
@require_auth
def get_dashboard(dashboard_id: UUID):
    """
    Get a single dashboard with its widgets for the authenticated user.

    Returns 404 if the dashboard does not exist OR belongs to a different user.

    Path Parameters:
        dashboard_id (UUID): Dashboard ID

    Returns:
        200: Dashboard with widgets
        401: Authentication required
        404: Dashboard not found
        500: Internal server error
    """
    try:
        user_id = g.current_user_id
        dashboard = _service.get_dashboard(dashboard_id, user_id=user_id)
        widgets = _service.list_widgets(dashboard_id, user_id=user_id)
        return success_response(data=_serialize_dashboard_with_widgets(dashboard, widgets))
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al obtener dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>", methods=["PUT"])
@require_auth
def update_dashboard(dashboard_id: UUID):
    """
    Update an existing dashboard for the authenticated user.

    Path Parameters:
        dashboard_id (UUID): Dashboard ID

    Request Body:
        DashboardUpdate schema

    Returns:
        200: Updated dashboard
        400: Validation error
        401: Authentication required
        404: Dashboard not found
        500: Internal server error
    """
    try:
        body = DashboardUpdate.model_validate(request.get_json(force=True) or {})
        dashboard = _service.update_dashboard(
            dashboard_id, user_id=g.current_user_id, data=body
        )
        return success_response(data=_serialize_dashboard(dashboard))
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=serialize_pydantic_errors(exc.errors()))
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al actualizar dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>", methods=["DELETE"])
@require_auth
def delete_dashboard(dashboard_id: UUID):
    """
    Delete a dashboard for the authenticated user.

    Path Parameters:
        dashboard_id (UUID): Dashboard ID

    Returns:
        200: Dashboard deleted successfully
        401: Authentication required
        404: Dashboard not found
        500: Internal server error
    """
    try:
        _service.delete_dashboard(dashboard_id, user_id=g.current_user_id)
        return success_response(message="Dashboard eliminado correctamente.")
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al eliminar dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>/widgets", methods=["POST"])
@require_auth
def create_widget(dashboard_id: UUID):
    """
    Create a new widget for a dashboard owned by the authenticated user.

    Path Parameters:
        dashboard_id (UUID): Dashboard ID

    Request Body:
        WidgetCreate schema

    Returns:
        201: Widget created (or 200 if idempotent duplicate)
        400: Validation error
        401: Authentication required
        404: Dashboard not found
        500: Internal server error
    """
    try:
        body = WidgetCreate.model_validate(request.get_json(force=True) or {})
        widget, created = _service.create_widget(
            dashboard_id, user_id=g.current_user_id, data=body
        )
        status = 201 if created else 200
        return success_response(data=_serialize_widget(widget), status_code=status)
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=serialize_pydantic_errors(exc.errors()))
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al crear widget: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>/widgets/<uuid:widget_id>", methods=["PUT"])
@require_auth
def update_widget(dashboard_id: UUID, widget_id: UUID):
    """
    Update an existing widget for the authenticated user.

    Path Parameters:
        dashboard_id (UUID): Dashboard ID
        widget_id (UUID): Widget ID

    Request Body:
        WidgetUpdate schema

    Returns:
        200: Updated widget
        400: Validation error
        401: Authentication required
        404: Dashboard or widget not found
        500: Internal server error
    """
    try:
        body = WidgetUpdate.model_validate(request.get_json(force=True) or {})
        widget = _service.update_widget(
            dashboard_id, widget_id, user_id=g.current_user_id, data=body
        )
        return success_response(data=_serialize_widget(widget))
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=serialize_pydantic_errors(exc.errors()))
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al actualizar widget: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>/widgets/<uuid:widget_id>", methods=["DELETE"])
@require_auth
def delete_widget(dashboard_id: UUID, widget_id: UUID):
    """
    Delete a widget from a dashboard for the authenticated user.

    Path Parameters:
        dashboard_id (UUID): Dashboard ID
        widget_id (UUID): Widget ID

    Returns:
        200: Widget deleted successfully
        401: Authentication required
        404: Dashboard or widget not found
        500: Internal server error
    """
    try:
        _service.delete_widget(dashboard_id, widget_id, user_id=g.current_user_id)
        return success_response(message="Widget eliminado correctamente.")
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al eliminar widget: {exc}", status_code=500)
