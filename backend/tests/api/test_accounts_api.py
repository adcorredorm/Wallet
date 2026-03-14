"""
API tests for account endpoints.

These tests use the Flask test client and mock the AccountService to verify
HTTP behaviour (status codes, response shape) in isolation from the database.
"""

import json
import pytest
from unittest.mock import patch
from uuid import uuid4

from app.utils.exceptions import NotFoundError, BusinessRuleError


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

            response = client.delete(f"/api/v1/accounts/{account_id}/permanent")
            data = response.get_json()

        assert response.status_code == 200
        assert data["success"] is True
        assert "eliminada permanentemente" in data["message"]
        mock_service.delete.assert_called_once_with(account_id)

    def test_hard_delete_returns_422_when_account_has_movements(self, client, account_id):
        """Should return 422 when account has transactions or transfers."""
        error_msg = (
            "No se puede eliminar una cuenta con transacciones. "
            "Use archivar en su lugar."
        )
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.delete.side_effect = BusinessRuleError(error_msg)

            response = client.delete(f"/api/v1/accounts/{account_id}/permanent")
            data = response.get_json()

        assert response.status_code == 422
        assert data["success"] is False
        assert data["message"] == error_msg

    def test_hard_delete_returns_404_when_account_not_found(self, client, account_id):
        """Should return 404 when the account does not exist."""
        exc = NotFoundError("Account", str(account_id))
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.delete.side_effect = exc

            response = client.delete(f"/api/v1/accounts/{account_id}/permanent")
            data = response.get_json()

        assert response.status_code == 404
        assert data["success"] is False
        assert data["message"] == exc.message
