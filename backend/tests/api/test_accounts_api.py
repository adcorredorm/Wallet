"""
API tests for account endpoints.

These tests use the Flask test client and mock the AccountService to verify
HTTP behaviour (status codes, response shape) in isolation from the database.

All endpoints require @require_auth, so every request includes a valid JWT
built from the test JWT_SECRET.
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, ANY
from uuid import uuid4

import jwt

from app.utils.exceptions import NotFoundError, BusinessRuleError


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

_TEST_USER_ID = uuid4()
_JWT_SECRET = "test-jwt-secret-for-testing-only"


def _auth_headers(user_id=None) -> dict:
    """Build a valid Authorization header for the given user_id."""
    uid = user_id or _TEST_USER_ID
    payload = {
        "sub": str(uid),
        "email": "api-test@example.com",
        "name": "API Test",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, _JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def account_id():
    """Return a fixed UUID for use across tests in this module."""
    return uuid4()


# ---------------------------------------------------------------------------
# DELETE /api/v1/accounts/<id>/permanent
# ---------------------------------------------------------------------------

class TestHardDeleteAccount:
    """Tests for DELETE /api/v1/accounts/<id>/permanent."""

    def test_hard_delete_returns_200_with_message(self, client, account_id):
        """Should return 200 and confirmation message when delete succeeds."""
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.delete.return_value = None

            response = client.delete(
                f"/api/v1/accounts/{account_id}/permanent",
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 200
        assert data["success"] is True
        assert "eliminada permanentemente" in data["message"]
        mock_service.delete.assert_called_once_with(account_id, user_id=ANY)

    def test_hard_delete_returns_422_when_account_has_movements(self, client, account_id):
        """Should return 422 when account has transactions or transfers."""
        error_msg = (
            "No se puede eliminar una cuenta con transacciones. "
            "Use archivar en su lugar."
        )
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.delete.side_effect = BusinessRuleError(error_msg)

            response = client.delete(
                f"/api/v1/accounts/{account_id}/permanent",
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 422
        assert data["success"] is False
        assert data["message"] == error_msg

    def test_hard_delete_returns_404_when_account_not_found(self, client, account_id):
        """Should return 404 when the account does not exist."""
        exc = NotFoundError("Account", str(account_id))
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.delete.side_effect = exc

            response = client.delete(
                f"/api/v1/accounts/{account_id}/permanent",
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 404
        assert data["success"] is False
        assert data["message"] == exc.message
