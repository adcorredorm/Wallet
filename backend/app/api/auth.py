"""
Authentication endpoints.

All endpoints in this blueprint are PUBLIC — no @require_auth decorator.
They handle Google OAuth login, refresh token rotation, and logout.

Endpoints:
    POST /auth/google   — exchange Google id_token for JWT + refresh token
    POST /auth/refresh  — rotate refresh token, get new JWT
    POST /auth/logout   — revoke refresh token (idempotent, always 204)
"""

from flask import Blueprint, request

from app.services.auth import AuthService
from app.utils.exceptions import ValidationError
from app.utils.responses import error_response, success_response

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_service = AuthService()


@auth_bp.route("/google", methods=["POST"])
def google_login():
    """
    Authenticate via Google OAuth.

    Validates the Google id_token locally, finds or creates the user,
    and returns a JWT + refresh token pair.

    Request Body:
        id_token (str): Google id_token from the frontend Google Sign-In SDK.

    Returns:
        200: access_token, refresh_token, user info, is_new_user flag.
        400: Missing or invalid request body.
        401: Google token validation failed.
    """
    body = request.get_json(silent=True) or {}
    id_token_str = body.get("id_token")
    if not id_token_str:
        return error_response("El campo 'id_token' es requerido", status_code=400)

    try:
        google_payload = auth_service.verify_google_token(id_token_str)
    except ValidationError as e:
        return error_response(e.message, status_code=401)

    user, is_new_user = auth_service.find_or_create_user(google_payload)
    tokens = auth_service.issue_tokens(user)

    return success_response(
        data={
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": user.to_dict(),
            "is_new_user": is_new_user,
        }
    )


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """
    Rotate a refresh token and issue a new JWT.

    The old refresh token is deleted and a new one is issued atomically.
    If the token does not exist or is expired, returns 401.

    Request Body:
        refresh_token (str): Opaque refresh token previously issued by this API.

    Returns:
        200: New access_token and refresh_token.
        400: Missing refresh_token field.
        401: Token not found, expired, or already rotated.
    """
    body = request.get_json(silent=True) or {}
    token_plain = body.get("refresh_token")
    if not token_plain:
        return error_response("El campo 'refresh_token' es requerido", status_code=400)

    try:
        tokens = auth_service.rotate_refresh_token(token_plain)
    except ValidationError as e:
        return error_response(e.message, status_code=401)

    return success_response(
        data={
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Revoke a refresh token (logout).

    Public endpoint — does not require a valid JWT, since the user may
    be logging out with an expired access token. Always returns 204.
    Idempotent: no-op if the token is not found.

    Request Body:
        refresh_token (str, optional): Opaque refresh token to revoke.

    Returns:
        204: Token revoked (or was already absent).
    """
    body = request.get_json(silent=True) or {}
    token_plain = body.get("refresh_token", "")
    if token_plain:
        auth_service.revoke_refresh_token(token_plain)
    return "", 204
