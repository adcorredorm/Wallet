"""
Recurring Rules API endpoints.

All routes are protected by @require_auth. The authenticated user's UUID is
read from g.current_user_id and forwarded to every service call.
"""

from datetime import datetime, timezone
from uuid import UUID

from flask import Blueprint, g, jsonify, make_response, request
from pydantic import ValidationError as PydanticValidationError

from app.schemas.recurring_rule import (
    RecurringRuleCreate,
    RecurringRuleUpdate,
    RecurringRuleResponse,
    RecurringRuleFilters,
)
from app.services.recurring_rule import RecurringRuleService
from app.repositories.recurring_rule import RecurringRuleRepository
from app.utils.auth import require_auth
from app.utils.exceptions import NotFoundError
from app.utils.responses import (
    success_response,
    error_response,
    serialize_pydantic_errors,
    paginated_response,
)
from app.utils.sync_cursor import decode_cursor, encode_cursor

recurring_rules_bp = Blueprint(
    "recurring_rules", __name__, url_prefix="/api/v1/recurring-rules"
)
recurring_rule_service = RecurringRuleService()
_repo = RecurringRuleRepository()


def _parse_client_updated_at(header_value: str | None) -> datetime | None:
    """Parse X-Client-Updated-At header into a UTC-aware datetime, or None."""
    if not header_value:
        return None
    try:
        dt = datetime.fromisoformat(header_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


@recurring_rules_bp.route("", methods=["GET"])
@require_auth
def list_recurring_rules():
    """
    List recurring rules with optional filters and sync cursor support.

    When the ``If-Sync-Cursor`` header is present and valid the endpoint
    operates in incremental sync mode: only rules modified since the cursor
    timestamp are returned as a flat list. Returns 304 when nothing changed.

    Request Headers:
        If-Sync-Cursor (str, optional): Opaque cursor from a previous response.

    Query Parameters:
        status (str): Filter by status ('active', 'paused', 'completed').
        account_id (UUID): Filter by account.
        category_id (UUID): Filter by category.
        page (int): Page number (default 1, ignored in incremental mode).
        limit (int): Items per page (default 20, max 10000).

    Returns:
        200: Paginated list (full sync) or flat list (incremental).
        304: No changes since cursor.
        400: Validation error.
        500: Internal server error.
    """
    try:
        user_id = g.current_user_id
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()

        if updated_since is not None:
            rules, _ = recurring_rule_service.get_filtered(
                user_id=user_id,
                updated_since=updated_since,
                limit=10000,
                page=1,
            )
            if not rules:
                resp = make_response("", 304)
                resp.headers["X-Sync-Cursor"] = new_cursor
                return resp
            data = [
                RecurringRuleResponse.model_validate(r).model_dump(mode="json")
                for r in rules
            ]
            resp = make_response(jsonify({"success": True, "data": data}), 200)
            resp.headers["X-Sync-Cursor"] = new_cursor
            return resp

        # Full sync mode
        filters_data = {
            "status": request.args.get("status"),
            "account_id": request.args.get("account_id"),
            "category_id": request.args.get("category_id"),
            "page": int(request.args.get("page", 1)),
            "limit": min(int(request.args.get("limit", 20)), 10000),
        }
        filters = RecurringRuleFilters(**filters_data)

        rules, total = recurring_rule_service.get_filtered(
            user_id=user_id,
            status=filters.status.value if filters.status else None,
            account_id=filters.account_id,
            category_id=filters.category_id,
            page=filters.page,
            limit=filters.limit,
        )

        items = [
            RecurringRuleResponse.model_validate(r).model_dump(mode="json")
            for r in rules
        ]
        body, status_code = paginated_response(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.limit,
        )
        resp = make_response(jsonify(body), status_code)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp

    except PydanticValidationError as e:
        return error_response(
            "Error de validación",
            status_code=400,
            errors=serialize_pydantic_errors(e.errors()),
        )
    except Exception as e:
        return error_response(f"Error al listar reglas: {str(e)}", status_code=500)


@recurring_rules_bp.route("", methods=["POST"])
@require_auth
def create_recurring_rule():
    """
    Create a new recurring rule.

    Request Body:
        RecurringRuleCreate schema.

    Returns:
        201: Created rule.
        400: Validation error.
        409: Duplicate offline_id.
        500: Internal server error.
    """
    try:
        body = RecurringRuleCreate(**request.json)

        # Idempotency check — return 409 if offline_id already exists for this user
        existing = _repo.get_by_offline_id(body.offline_id, g.current_user_id)
        if existing:
            return error_response(
                "A recurring rule with this offline_id already exists",
                status_code=409,
                errors={"code": "DUPLICATE_OFFLINE_ID"},
            )

        rule = recurring_rule_service.create(
            user_id=g.current_user_id,
            offline_id=body.offline_id,
            title=body.title,
            type=body.type.value,
            amount=body.amount,
            account_id=body.account_id,
            category_id=body.category_id,
            frequency=body.frequency.value,
            start_date=body.start_date,
            next_occurrence_date=body.next_occurrence_date,
            interval=body.interval,
            description=body.description,
            tags=body.tags,
            requires_confirmation=body.requires_confirmation,
            day_of_week=body.day_of_week,
            day_of_month=body.day_of_month,
            end_date=body.end_date,
            max_occurrences=body.max_occurrences,
            status=body.status.value,
        )

        data = RecurringRuleResponse.model_validate(rule).model_dump(mode="json")
        return success_response(
            data=data,
            message="Regla recurrente creada exitosamente",
            status_code=201,
        )

    except PydanticValidationError as e:
        return error_response(
            "Error de validación",
            status_code=400,
            errors=serialize_pydantic_errors(e.errors()),
        )
    except Exception as e:
        return error_response(f"Error al crear regla: {str(e)}", status_code=500)


@recurring_rules_bp.route("/<uuid:rule_id>", methods=["PATCH"])
@require_auth
def update_recurring_rule(rule_id: UUID):
    """
    Update an existing recurring rule.

    Supports Last-Write-Wins conflict detection via X-Client-Updated-At header.

    Path Parameters:
        rule_id (UUID): RecurringRule ID.

    Request Headers:
        X-Client-Updated-At (str, optional): ISO-8601 timestamp of the version
            the client last observed.

    Request Body:
        RecurringRuleUpdate schema (all fields optional).

    Returns:
        200: Updated rule.
        400: Validation error.
        404: Rule not found.
        409: Conflict — server version is newer.
        500: Internal server error.
    """
    try:
        body = RecurringRuleUpdate(**request.json)
        user_id = g.current_user_id

        client_updated_at = _parse_client_updated_at(
            request.headers.get("X-Client-Updated-At")
        )
        if client_updated_at is not None:
            current = recurring_rule_service.get_by_id(rule_id, user_id=user_id)
            server_updated_at = current.updated_at
            if server_updated_at.tzinfo is None:
                server_updated_at = server_updated_at.replace(tzinfo=timezone.utc)
            if server_updated_at > client_updated_at:
                server_data = RecurringRuleResponse.model_validate(current).model_dump(
                    mode="json"
                )
                return error_response(
                    "Conflicto: el servidor tiene una version mas reciente",
                    status_code=409,
                    errors={"server_version": server_data},
                )

        # Convert Pydantic model to dict, skipping unset fields
        update_kwargs = body.model_dump(exclude_unset=True)
        # Convert enum fields to string values for the service layer
        for enum_field in ("type", "frequency", "status"):
            if enum_field in update_kwargs and update_kwargs[enum_field] is not None:
                update_kwargs[enum_field] = update_kwargs[enum_field].value

        rule = recurring_rule_service.update(rule_id, user_id, **update_kwargs)
        data = RecurringRuleResponse.model_validate(rule).model_dump(mode="json")
        return success_response(data=data, message="Regla recurrente actualizada exitosamente")

    except PydanticValidationError as e:
        return error_response(
            "Error de validación",
            status_code=400,
            errors=serialize_pydantic_errors(e.errors()),
        )
    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al actualizar regla: {str(e)}", status_code=500)


@recurring_rules_bp.route("/<uuid:rule_id>", methods=["DELETE"])
@require_auth
def delete_recurring_rule(rule_id: UUID):
    """
    Delete a recurring rule (hard delete).

    Path Parameters:
        rule_id (UUID): RecurringRule ID.

    Returns:
        204: No content.
        404: Rule not found.
        500: Internal server error.
    """
    try:
        recurring_rule_service.delete(rule_id, user_id=g.current_user_id)
        return make_response("", 204)

    except NotFoundError as e:
        return error_response(e.message, status_code=404)
    except Exception as e:
        return error_response(f"Error al eliminar regla: {str(e)}", status_code=500)
