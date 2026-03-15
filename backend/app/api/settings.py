"""
Settings API endpoints.

Provides read and write access to per-user configuration stored in
the ``user_settings`` table.  Each setting is identified by a well-known key
(e.g. ``primary_currency``).  Writes are validated in the service layer;
unknown keys and invalid values are rejected with 422.

Note: ``@require_auth`` decorator and ``g.current_user_id`` injection are
applied in Chunk 2 (Task 2.1). Until then, endpoints require the decorator
to be wired but are not directly callable without auth context.
"""

from flask import Blueprint, g, request
from pydantic import ValidationError as PydanticValidationError

from app.schemas.user_setting import SettingResponse, SettingUpdateRequest, SettingsResponse
from app.services.user_setting import SettingsService
from app.utils.exceptions import ValidationError
from app.utils.responses import error_response, success_response

settings_bp = Blueprint("settings", __name__, url_prefix="/api/v1")
settings_service = SettingsService()


@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    """
    Return all stored settings for the authenticated user.

    Returns:
        200: SettingsResponse with a flat ``{key: value}`` dictionary.
        500: Internal server error.
    """
    try:
        all_settings = settings_service.get_all(user_id=g.current_user_id)
        response = SettingsResponse(settings=all_settings)
        return success_response(data=response.model_dump(mode="json"))

    except Exception as e:
        return error_response(
            f"Error al obtener configuración: {str(e)}", status_code=500
        )


@settings_bp.route("/settings/<string:key>", methods=["PUT"])
def update_setting(key: str):
    """
    Update a single setting by key for the authenticated user.

    Path Parameters:
        key (str): Setting identifier (e.g. ``primary_currency``).

    Request Body:
        ``{ "value": <any> }`` — validated as SettingUpdateRequest.

    Returns:
        200: SettingResponse with the persisted key, value, and updated_at.
        422: Unknown key, invalid value, or malformed request body.
        500: Internal server error.
    """
    try:
        body = request.get_json(silent=True) or {}
        update_data = SettingUpdateRequest(**body)

        setting = settings_service.set(
            user_id=g.current_user_id,
            key=key,
            value=update_data.value,
        )

        response = SettingResponse.model_validate(setting)
        return success_response(data=response.model_dump(mode="json"))

    except PydanticValidationError as e:
        return error_response(
            "Error de validación en el cuerpo de la solicitud",
            status_code=422,
            errors=e.errors(),
        )
    except ValidationError as e:
        return error_response(e.message, status_code=422)
    except Exception as e:
        return error_response(
            f"Error al actualizar configuración: {str(e)}", status_code=500
        )
