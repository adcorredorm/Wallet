"""
API tests for account endpoints.

These tests use the Flask test client and mock the AccountService to verify
HTTP behaviour (status codes, response shape) in isolation from the database.

All endpoints require @require_auth, so every request includes a valid JWT
built from the test JWT_SECRET.
"""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, ANY
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
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
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


# ---------------------------------------------------------------------------
# TDD: balance field removed from list/detail; /balance endpoint deleted
# ---------------------------------------------------------------------------


def _make_mock_account(account_id=None):
    """Build a minimal mock account compatible with AccountResponse.model_validate."""
    account = MagicMock()
    account.id = account_id or uuid4()
    account.name = "Cuenta TDD"
    account.type = "debit"
    account.currency = "MXN"
    account.description = None
    account.tags = []
    account.active = True
    account.sort_order = 0
    account.icon = None
    now = datetime.now(timezone.utc)
    account.created_at = now
    account.updated_at = now
    return account


class TestListAccountsNoBalance:
    """GET /api/v1/accounts must NOT include a balance key in each item."""

    def test_list_accounts_response_has_no_balance_field(self, client):
        """Full-sync response items must not contain a balance key."""
        mock_account = _make_mock_account()
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.get_all.return_value = [mock_account]

            response = client.get(
                "/api/v1/accounts",
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 200
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert "balance" not in data["data"][0], (
            "balance field must be absent from list response items"
        )

    def test_list_accounts_incremental_response_has_no_balance_field(self, client):
        """Incremental-sync response items must not contain a balance key."""
        mock_account = _make_mock_account()
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.get_all.return_value = [mock_account]
            with patch("app.api.accounts.decode_cursor") as mock_decode:
                mock_decode.return_value = datetime(2026, 1, 1)

                response = client.get(
                    "/api/v1/accounts",
                    headers={**_auth_headers(), "If-Sync-Cursor": "some-cursor"},
                )
                data = response.get_json()

        assert response.status_code == 200
        assert len(data["data"]) == 1
        assert "balance" not in data["data"][0], (
            "balance field must be absent from incremental sync response items"
        )

    def test_list_accounts_calls_get_all_not_get_all_with_balances(self, client):
        """list_accounts must use account_service.get_all, not get_all_with_balances."""
        mock_account = _make_mock_account()
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.get_all.return_value = [mock_account]

            client.get("/api/v1/accounts", headers=_auth_headers())

            mock_service.get_all.assert_called_once()
            assert not hasattr(mock_service, "get_all_with_balances") or \
                not mock_service.get_all_with_balances.called, (
                "get_all_with_balances must not be called"
            )


class TestGetAccountNoBalance:
    """GET /api/v1/accounts/<id> must NOT include a balance key."""

    def test_get_account_response_has_no_balance_field(self, client, account_id):
        """Single-account response must not contain a balance key."""
        mock_account = _make_mock_account(account_id)
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.get_by_id.return_value = mock_account

            response = client.get(
                f"/api/v1/accounts/{account_id}",
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 200
        assert data["success"] is True
        assert "balance" not in data["data"], (
            "balance field must be absent from single account response"
        )

    def test_get_account_calls_get_by_id_not_get_with_balance(self, client, account_id):
        """get_account must use account_service.get_by_id, not get_with_balance."""
        mock_account = _make_mock_account(account_id)
        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.get_by_id.return_value = mock_account

            client.get(f"/api/v1/accounts/{account_id}", headers=_auth_headers())

            mock_service.get_by_id.assert_called_once()
            assert not hasattr(mock_service, "get_with_balance") or \
                not mock_service.get_with_balance.called, (
                "get_with_balance must not be called"
            )


class TestBalanceEndpointDeleted:
    """GET /api/v1/accounts/<id>/balance must not exist as a registered route."""

    def test_balance_endpoint_is_not_registered(self, app, account_id):
        """The /balance route must not appear in the URL map after removal."""
        registered_rules = [str(rule) for rule in app.url_map.iter_rules()]
        balance_routes = [
            r for r in registered_rules if "/balance" in r
        ]
        assert balance_routes == [], (
            f"Found /balance routes that should have been removed: {balance_routes}"
        )
