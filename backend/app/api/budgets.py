# backend/app/api/budgets.py
from datetime import datetime, timezone
from uuid import UUID

from flask import Blueprint, g, jsonify, make_response, request
from pydantic import ValidationError as PydanticValidationError

from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services.budget import BudgetService
from app.repositories.budget import BudgetRepository
from app.utils.auth import require_auth
from app.utils.exceptions import NotFoundError
from app.utils.responses import success_response, error_response, serialize_pydantic_errors
from app.utils.sync_cursor import decode_cursor, encode_cursor

budgets_bp = Blueprint("budgets", __name__, url_prefix="/api/v1/budgets")
budget_service = BudgetService()
_repo = BudgetRepository()


def _parse_client_updated_at(header_value: str | None) -> datetime | None:
    if not header_value:
        return None
    try:
        dt = datetime.fromisoformat(header_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


@budgets_bp.route("", methods=["GET"])
@require_auth
def list_budgets():
    try:
        user_id = g.current_user_id
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()

        budgets = budget_service.get_active(user_id=user_id, updated_since=updated_since)

        if updated_since is not None and not budgets:
            resp = make_response("", 304)
            resp.headers["X-Sync-Cursor"] = new_cursor
            return resp

        data = [BudgetResponse.model_validate(b).model_dump(mode="json") for b in budgets]

        if updated_since is not None:
            resp = make_response(jsonify({"success": True, "data": data}), 200)
        else:
            resp = make_response(
                jsonify({"success": True, "data": {"items": data, "total": len(data)}}), 200
            )
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp

    except Exception as e:
        return error_response(f"Error al listar presupuestos: {str(e)}", status_code=500)


@budgets_bp.route("/<uuid:budget_id>", methods=["GET"])
@require_auth
def get_budget(budget_id: UUID):
    try:
        budget = budget_service.get_by_id(budget_id, g.current_user_id)
        data = BudgetResponse.model_validate(budget).model_dump(mode="json")
        return success_response(data=data)
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error: {str(e)}", status_code=500)


@budgets_bp.route("", methods=["POST"])
@require_auth
def create_budget():
    try:
        body = BudgetCreate(**request.json)

        existing = _repo.get_by_offline_id(body.offline_id, g.current_user_id)
        if existing:
            return error_response(
                "A budget with this offline_id already exists",
                status_code=409,
                errors={"code": "DUPLICATE_OFFLINE_ID"},
            )

        budget = budget_service.create(
            user_id=g.current_user_id,
            offline_id=body.offline_id,
            name=body.name,
            account_id=body.account_id,
            category_id=body.category_id,
            amount_limit=body.amount_limit,
            currency=body.currency,
            budget_type=body.budget_type.value,
            frequency=body.frequency.value if body.frequency else None,
            interval=body.interval,
            reference_date=body.reference_date,
            start_date=body.start_date,
            end_date=body.end_date,
            status=body.status.value,
            icon=body.icon,
            color=body.color,
        )
        data = BudgetResponse.model_validate(budget).model_dump(mode="json")
        return success_response(data=data, message="Presupuesto creado exitosamente", status_code=201)

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=serialize_pydantic_errors(e.errors()))
    except Exception as e:
        return error_response(f"Error al crear presupuesto: {str(e)}", status_code=500)


@budgets_bp.route("/<uuid:budget_id>", methods=["PATCH"])
@require_auth
def update_budget(budget_id: UUID):
    try:
        body = BudgetUpdate(**request.json)
        user_id = g.current_user_id

        client_updated_at = _parse_client_updated_at(request.headers.get("X-Client-Updated-At"))
        if client_updated_at is not None:
            current = budget_service.get_by_id(budget_id, user_id)
            server_ts = current.updated_at
            if server_ts.tzinfo is None:
                server_ts = server_ts.replace(tzinfo=timezone.utc)
            if server_ts > client_updated_at:
                server_data = BudgetResponse.model_validate(current).model_dump(mode="json")
                return error_response(
                    "Conflicto: el servidor tiene una version mas reciente",
                    status_code=409,
                    errors={"server_version": server_data},
                )

        update_kwargs = body.model_dump(exclude_unset=True)
        for enum_field in ("frequency", "status"):
            if enum_field in update_kwargs and update_kwargs[enum_field] is not None:
                update_kwargs[enum_field] = update_kwargs[enum_field].value

        budget = budget_service.update(budget_id, user_id, **update_kwargs)
        data = BudgetResponse.model_validate(budget).model_dump(mode="json")
        return success_response(data=data, message="Presupuesto actualizado exitosamente")

    except PydanticValidationError as e:
        return error_response("Error de validación", status_code=400, errors=serialize_pydantic_errors(e.errors()))
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al actualizar presupuesto: {str(e)}", status_code=500)


@budgets_bp.route("/<uuid:budget_id>", methods=["DELETE"])
@require_auth
def archive_budget(budget_id: UUID):
    try:
        budget_service.archive(budget_id, g.current_user_id)
        return make_response("", 204)
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al archivar presupuesto: {str(e)}", status_code=500)


@budgets_bp.route("/<uuid:budget_id>/permanent", methods=["DELETE"])
@require_auth
def delete_budget_permanent(budget_id: UUID):
    try:
        budget_service.delete(budget_id, g.current_user_id)
        return make_response("", 204)
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al eliminar presupuesto: {str(e)}", status_code=500)
