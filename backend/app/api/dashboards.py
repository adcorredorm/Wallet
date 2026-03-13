"""
Dashboards blueprint — CRUD for user-defined analytics dashboards.

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

from flask import Blueprint, request
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
from app.utils.responses import success_response, error_response
from app.utils.exceptions import WalletException

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
def list_dashboards():
    try:
        dashboards = _service.list_dashboards()
        return success_response(data=[_serialize_dashboard(d) for d in dashboards])
    except Exception as exc:
        return error_response(f"Error al listar dashboards: {exc}", status_code=500)


@dashboards_bp.route("", methods=["POST"])
def create_dashboard():
    try:
        body = DashboardCreate.model_validate(request.get_json(force=True) or {})
        dashboard, created = _service.create_dashboard(body)
        status = 201 if created else 200
        return success_response(data=_serialize_dashboard(dashboard), status_code=status)
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=exc.errors())
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al crear dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>", methods=["GET"])
def get_dashboard(dashboard_id: UUID):
    try:
        dashboard = _service.get_dashboard(dashboard_id)
        widgets = _service.list_widgets(dashboard_id)
        return success_response(data=_serialize_dashboard_with_widgets(dashboard, widgets))
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al obtener dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>", methods=["PUT"])
def update_dashboard(dashboard_id: UUID):
    try:
        body = DashboardUpdate.model_validate(request.get_json(force=True) or {})
        dashboard = _service.update_dashboard(dashboard_id, body)
        return success_response(data=_serialize_dashboard(dashboard))
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=exc.errors())
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al actualizar dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>", methods=["DELETE"])
def delete_dashboard(dashboard_id: UUID):
    try:
        _service.delete_dashboard(dashboard_id)
        return success_response(data={"message": "Dashboard eliminado correctamente."})
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al eliminar dashboard: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>/widgets", methods=["POST"])
def create_widget(dashboard_id: UUID):
    try:
        body = WidgetCreate.model_validate(request.get_json(force=True) or {})
        widget, created = _service.create_widget(dashboard_id, body)
        status = 201 if created else 200
        return success_response(data=_serialize_widget(widget), status_code=status)
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=exc.errors())
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al crear widget: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>/widgets/<uuid:widget_id>", methods=["PUT"])
def update_widget(dashboard_id: UUID, widget_id: UUID):
    try:
        body = WidgetUpdate.model_validate(request.get_json(force=True) or {})
        widget = _service.update_widget(dashboard_id, widget_id, body)
        return success_response(data=_serialize_widget(widget))
    except ValidationError as exc:
        return error_response("Datos inválidos", status_code=400, errors=exc.errors())
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al actualizar widget: {exc}", status_code=500)


@dashboards_bp.route("/<uuid:dashboard_id>/widgets/<uuid:widget_id>", methods=["DELETE"])
def delete_widget(dashboard_id: UUID, widget_id: UUID):
    try:
        _service.delete_widget(dashboard_id, widget_id)
        return success_response(data={"message": "Widget eliminado correctamente."})
    except WalletException as exc:
        return error_response(exc.message, status_code=exc.status_code)
    except Exception as exc:
        return error_response(f"Error al eliminar widget: {exc}", status_code=500)
