"""
API tests for sort_order and icon fields on account endpoints.

These tests mock AccountService at the module level and verify:
- POST /api/v1/accounts includes sort_order + icon in request and response
- PUT /api/v1/accounts/:id includes sort_order + icon in request and response
- GET /api/v1/accounts includes sort_order + icon in each response item
- GET /api/v1/accounts/:id includes sort_order + icon in response
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from uuid import uuid4

import jwt


_TEST_USER_ID = uuid4()
_JWT_SECRET = "test-jwt-secret-for-testing-only"


def _auth_headers(user_id=None) -> dict:
    """Build a valid Authorization header."""
    uid = user_id or _TEST_USER_ID
    payload = {
        "sub": str(uid),
        "email": "sort-order-test@example.com",
        "name": "Sort Order Test",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, _JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _make_mock_account(sort_order: int = 0, icon: str | None = None, account_id=None):
    """Build a mock account with sort_order and icon attributes."""
    account = MagicMock()
    account.id = account_id or uuid4()
    account.name = "Cuenta Test"
    account.type = "debit"
    account.currency = "USD"
    account.description = None
    account.tags = []
    account.active = True
    account.sort_order = sort_order
    account.icon = icon
    now = datetime.now(timezone.utc)
    account.created_at = now
    account.updated_at = now
    return account


@pytest.fixture
def account_id():
    return uuid4()


class TestCreateAccountSortOrderIcon:
    """POST /api/v1/accounts — sort_order and icon in request + response."""

    def test_create_with_sort_order_and_icon_calls_service_correctly(self, client):
        """Service must receive sort_order=2 and icon='💳' from request body."""
        mock_account = _make_mock_account(sort_order=2, icon="💳")

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.create.return_value = mock_account

            response = client.post(
                "/api/v1/accounts",
                json={
                    "name": "Cuenta con icono",
                    "type": "debit",
                    "currency": "USD",
                    "sort_order": 2,
                    "icon": "💳",
                },
                headers=_auth_headers(),
            )

        assert response.status_code == 201
        call_kwargs = mock_service.create.call_args.kwargs
        assert call_kwargs["sort_order"] == 2
        assert call_kwargs["icon"] == "💳"

    def test_create_without_sort_order_passes_none_to_service(self, client):
        """When sort_order is omitted, service receives sort_order=None (triggers auto-assign)."""
        mock_account = _make_mock_account(sort_order=0, icon=None)

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.create.return_value = mock_account

            response = client.post(
                "/api/v1/accounts",
                json={"name": "Sin orden", "type": "cash", "currency": "USD"},
                headers=_auth_headers(),
            )

        assert response.status_code == 201
        call_kwargs = mock_service.create.call_args.kwargs
        assert call_kwargs["sort_order"] is None
        assert call_kwargs["icon"] is None

    def test_create_response_includes_sort_order_and_icon(self, client):
        """Response body must include sort_order and icon fields."""
        mock_account = _make_mock_account(sort_order=3, icon="💵")

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.create.return_value = mock_account

            response = client.post(
                "/api/v1/accounts",
                json={
                    "name": "Cuenta efectivo",
                    "type": "cash",
                    "currency": "USD",
                    "sort_order": 3,
                    "icon": "💵",
                },
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 201
        assert data["data"]["sort_order"] == 3
        assert data["data"]["icon"] == "💵"

    def test_create_response_includes_null_icon(self, client):
        """icon can be null in response."""
        mock_account = _make_mock_account(sort_order=0, icon=None)

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.create.return_value = mock_account

            response = client.post(
                "/api/v1/accounts",
                json={"name": "Sin icono", "type": "debit", "currency": "USD"},
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 201
        assert data["data"]["sort_order"] == 0
        assert data["data"]["icon"] is None

    def test_create_rejects_negative_sort_order(self, client):
        """sort_order must be >= 0; negative value should return 400."""
        with patch("app.api.accounts.account_service"):
            response = client.post(
                "/api/v1/accounts",
                json={
                    "name": "Orden negativo",
                    "type": "debit",
                    "currency": "USD",
                    "sort_order": -1,
                },
                headers=_auth_headers(),
            )

        assert response.status_code == 400

    def test_create_rejects_icon_over_50_chars(self, client):
        """icon must be <= 50 chars; longer strings should return 400."""
        with patch("app.api.accounts.account_service"):
            response = client.post(
                "/api/v1/accounts",
                json={
                    "name": "Icono largo",
                    "type": "debit",
                    "currency": "USD",
                    "icon": "x" * 51,
                },
                headers=_auth_headers(),
            )

        assert response.status_code == 400


class TestUpdateAccountSortOrderIcon:
    """PUT /api/v1/accounts/:id — sort_order and icon in request + response."""

    def test_update_with_sort_order_and_icon_calls_service_correctly(
        self, client, account_id
    ):
        """Service must receive sort_order=5 and icon='🏦' from PUT body."""
        mock_account = _make_mock_account(sort_order=5, icon="🏦", account_id=account_id)

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.update.return_value = mock_account
            response = client.put(
                f"/api/v1/accounts/{account_id}",
                json={"sort_order": 5, "icon": "🏦"},
                headers=_auth_headers(),
            )

        assert response.status_code == 200
        call_kwargs = mock_service.update.call_args.kwargs
        assert call_kwargs["sort_order"] == 5
        assert call_kwargs["icon"] == "🏦"

    def test_update_without_sort_order_passes_none(self, client, account_id):
        """When sort_order is omitted from PUT body, service receives sort_order=None."""
        mock_account = _make_mock_account(sort_order=0, account_id=account_id)

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.update.return_value = mock_account

            response = client.put(
                f"/api/v1/accounts/{account_id}",
                json={"name": "Nombre nuevo"},
                headers=_auth_headers(),
            )

        assert response.status_code == 200
        call_kwargs = mock_service.update.call_args.kwargs
        assert call_kwargs["sort_order"] is None

    def test_update_response_includes_sort_order_and_icon(self, client, account_id):
        """Response body must include sort_order and icon after update."""
        mock_account = _make_mock_account(sort_order=2, icon="💰", account_id=account_id)

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.update.return_value = mock_account

            response = client.put(
                f"/api/v1/accounts/{account_id}",
                json={"sort_order": 2, "icon": "💰"},
                headers=_auth_headers(),
            )
            data = response.get_json()

        assert response.status_code == 200
        assert data["data"]["sort_order"] == 2
        assert data["data"]["icon"] == "💰"

    def test_update_rejects_negative_sort_order(self, client, account_id):
        """PUT with sort_order < 0 must return 400."""
        with patch("app.api.accounts.account_service"):
            response = client.put(
                f"/api/v1/accounts/{account_id}",
                json={"sort_order": -5},
                headers=_auth_headers(),
            )

        assert response.status_code == 400


class TestListAccountsSortOrderIcon:
    """GET /api/v1/accounts — sort_order and icon present in response items."""

    def test_list_accounts_includes_sort_order_and_icon_in_items(self, client):
        """Each account in list response must have sort_order and icon keys."""
        mock_account = _make_mock_account(sort_order=1, icon="💳")

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.get_all.return_value = [mock_account]

            response = client.get("/api/v1/accounts", headers=_auth_headers())
            data = response.get_json()

        assert response.status_code == 200
        assert len(data["data"]) == 1
        item = data["data"][0]
        assert "sort_order" in item
        assert item["sort_order"] == 1
        assert "icon" in item
        assert item["icon"] == "💳"


class TestGetAccountSortOrderIcon:
    """GET /api/v1/accounts/:id — sort_order and icon present in response."""

    def test_get_account_includes_sort_order_and_icon(self, client, account_id):
        """Single-account response must include sort_order and icon."""
        mock_account = _make_mock_account(
            sort_order=4, icon="💵", account_id=account_id
        )

        with patch("app.api.accounts.account_service") as mock_service:
            mock_service.get_by_id.return_value = mock_account

            response = client.get(
                f"/api/v1/accounts/{account_id}", headers=_auth_headers()
            )
            data = response.get_json()

        assert response.status_code == 200
        assert data["data"]["sort_order"] == 4
        assert data["data"]["icon"] == "💵"
