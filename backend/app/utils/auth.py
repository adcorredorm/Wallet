"""
Authentication utilities: JWT verification and require_auth decorator.

The decorator extracts and verifies the JWT from the Authorization header,
injects g.current_user_id as a UUID, and returns 401 on any failure.
Endpoints decorated with @require_auth cannot be reached without a valid token.
"""

import uuid
from functools import wraps
from typing import Any, Callable

import jwt
from flask import current_app, g, request

from app.utils.responses import error_response


def _extract_bearer_token() -> str | None:
    """
    Extract the Bearer token from the Authorization header.

    Returns:
        Token string if header is present and well-formed, else None.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header[len("Bearer "):]


def verify_jwt(token: str) -> dict[str, Any]:
    """
    Verify a JWT token and return its decoded payload.

    Args:
        token: Raw JWT string (without 'Bearer ' prefix).

    Returns:
        Decoded payload dict containing at least 'sub', 'email', 'name'.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is malformed or signature is invalid.
    """
    return jwt.decode(
        token,
        current_app.config["JWT_SECRET"],
        algorithms=["HS256"],
    )


def require_auth(f: Callable) -> Callable:
    """
    Decorator that enforces JWT authentication on a Flask route.

    Extracts the Bearer token from the Authorization header, verifies it,
    and injects g.current_user_id (UUID) for use in the route handler.
    The user UUID is read from the 'sub' claim of the JWT payload.

    Returns 401 if the header is missing, token is malformed, or token
    is expired.

    Args:
        f: The Flask view function to protect.

    Returns:
        Wrapped function that performs auth before delegating to f.
    """

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        token = _extract_bearer_token()
        if not token:
            return error_response("Autenticación requerida", status_code=401)

        try:
            payload = verify_jwt(token)
        except jwt.ExpiredSignatureError:
            return error_response("Token expirado", status_code=401)
        except jwt.InvalidTokenError:
            return error_response("Token inválido", status_code=401)

        try:
            g.current_user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError):
            return error_response("Token inválido: payload malformado", status_code=401)

        return f(*args, **kwargs)

    return decorated
