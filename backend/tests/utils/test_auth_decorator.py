"""Tests for the @require_auth decorator."""
import pytest
import jwt
from datetime import datetime, timedelta
from flask import g
from app.utils.auth import require_auth


@pytest.fixture
def valid_token(app):
    """Generate a valid JWT for testing."""
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "test@example.com",
        "name": "Test User",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")


@pytest.fixture
def expired_token(app):
    """Generate an expired JWT for testing."""
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "test@example.com",
        "name": "Test User",
        "exp": datetime.utcnow() - timedelta(hours=1),
    }
    return jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")


def test_require_auth_sets_current_user_id(app, valid_token):
    """require_auth injects g.current_user_id from a valid Bearer token."""
    with app.test_request_context(
        "/",
        headers={"Authorization": f"Bearer {valid_token}"},
    ):
        @require_auth
        def protected():
            return str(g.current_user_id)

        result = protected()
        assert "00000000-0000-0000-0000-000000000001" in result


def test_require_auth_returns_401_without_header(app):
    """require_auth returns 401 when Authorization header is absent."""
    with app.test_request_context("/"):
        @require_auth
        def protected():
            return "ok"

        response, status = protected()
        assert status == 401


def test_require_auth_returns_401_on_expired_token(app, expired_token):
    """require_auth returns 401 for expired tokens."""
    with app.test_request_context(
        "/",
        headers={"Authorization": f"Bearer {expired_token}"},
    ):
        @require_auth
        def protected():
            return "ok"

        response, status = protected()
        assert status == 401


def test_require_auth_returns_401_on_malformed_token(app):
    """require_auth returns 401 for non-JWT garbage."""
    with app.test_request_context(
        "/",
        headers={"Authorization": "Bearer not.a.jwt"},
    ):
        @require_auth
        def protected():
            return "ok"

        response, status = protected()
        assert status == 401
