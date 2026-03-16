"""
Tests that verify @require_auth is applied to all non-auth endpoints.

Every endpoint in accounts, categories, transactions, transfers, dashboard,
dashboards, exchange_rates, and settings must return 401 when no Authorization
header is provided.
"""

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def uid():
    """A placeholder UUID string for path parameters."""
    from uuid import uuid4
    return str(uuid4())


def _assert_401(response, path: str) -> None:
    """Helper: assert the response is 401 Unauthorized."""
    assert response.status_code == 401, (
        f"Expected 401 for {path}, got {response.status_code}. "
        "Add @require_auth to this endpoint."
    )


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class TestAccountsRequireAuth:
    def test_list_accounts_requires_auth(self, client):
        resp = client.get("/api/v1/accounts")
        _assert_401(resp, "GET /api/v1/accounts")

    def test_get_account_requires_auth(self, client, uid):
        resp = client.get(f"/api/v1/accounts/{uid}")
        _assert_401(resp, f"GET /api/v1/accounts/{uid}")

    def test_create_account_requires_auth(self, client):
        resp = client.post("/api/v1/accounts", json={})
        _assert_401(resp, "POST /api/v1/accounts")

    def test_update_account_requires_auth(self, client, uid):
        resp = client.put(f"/api/v1/accounts/{uid}", json={})
        _assert_401(resp, f"PUT /api/v1/accounts/{uid}")

    def test_delete_account_requires_auth(self, client, uid):
        resp = client.delete(f"/api/v1/accounts/{uid}")
        _assert_401(resp, f"DELETE /api/v1/accounts/{uid}")

    def test_hard_delete_account_requires_auth(self, client, uid):
        resp = client.delete(f"/api/v1/accounts/{uid}/permanent")
        _assert_401(resp, f"DELETE /api/v1/accounts/{uid}/permanent")


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class TestCategoriesRequireAuth:
    def test_list_categories_requires_auth(self, client):
        resp = client.get("/api/v1/categories")
        _assert_401(resp, "GET /api/v1/categories")

    def test_get_category_requires_auth(self, client, uid):
        resp = client.get(f"/api/v1/categories/{uid}")
        _assert_401(resp, f"GET /api/v1/categories/{uid}")

    def test_create_category_requires_auth(self, client):
        resp = client.post("/api/v1/categories", json={})
        _assert_401(resp, "POST /api/v1/categories")

    def test_update_category_requires_auth(self, client, uid):
        resp = client.put(f"/api/v1/categories/{uid}", json={})
        _assert_401(resp, f"PUT /api/v1/categories/{uid}")

    def test_delete_category_requires_auth(self, client, uid):
        resp = client.delete(f"/api/v1/categories/{uid}")
        _assert_401(resp, f"DELETE /api/v1/categories/{uid}")

    def test_hard_delete_category_requires_auth(self, client, uid):
        resp = client.delete(f"/api/v1/categories/{uid}/permanent")
        _assert_401(resp, f"DELETE /api/v1/categories/{uid}/permanent")


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

class TestTransactionsRequireAuth:
    def test_list_transactions_requires_auth(self, client):
        resp = client.get("/api/v1/transactions")
        _assert_401(resp, "GET /api/v1/transactions")

    def test_get_transaction_requires_auth(self, client, uid):
        resp = client.get(f"/api/v1/transactions/{uid}")
        _assert_401(resp, f"GET /api/v1/transactions/{uid}")

    def test_create_transaction_requires_auth(self, client):
        resp = client.post("/api/v1/transactions", json={})
        _assert_401(resp, "POST /api/v1/transactions")

    def test_update_transaction_requires_auth(self, client, uid):
        resp = client.put(f"/api/v1/transactions/{uid}", json={})
        _assert_401(resp, f"PUT /api/v1/transactions/{uid}")

    def test_delete_transaction_requires_auth(self, client, uid):
        resp = client.delete(f"/api/v1/transactions/{uid}")
        _assert_401(resp, f"DELETE /api/v1/transactions/{uid}")


# ---------------------------------------------------------------------------
# Transfers
# ---------------------------------------------------------------------------

class TestTransfersRequireAuth:
    def test_list_transfers_requires_auth(self, client):
        resp = client.get("/api/v1/transfers")
        _assert_401(resp, "GET /api/v1/transfers")

    def test_get_transfer_requires_auth(self, client, uid):
        resp = client.get(f"/api/v1/transfers/{uid}")
        _assert_401(resp, f"GET /api/v1/transfers/{uid}")

    def test_create_transfer_requires_auth(self, client):
        resp = client.post("/api/v1/transfers", json={})
        _assert_401(resp, "POST /api/v1/transfers")

    def test_update_transfer_requires_auth(self, client, uid):
        resp = client.put(f"/api/v1/transfers/{uid}", json={})
        _assert_401(resp, f"PUT /api/v1/transfers/{uid}")

    def test_delete_transfer_requires_auth(self, client, uid):
        resp = client.delete(f"/api/v1/transfers/{uid}")
        _assert_401(resp, f"DELETE /api/v1/transfers/{uid}")


# ---------------------------------------------------------------------------
# Dashboard (analytics)
# ---------------------------------------------------------------------------

class TestDashboardRequireAuth:
    def test_get_dashboard_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard")
        _assert_401(resp, "GET /api/v1/dashboard")

    def test_get_net_worth_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/net-worth")
        _assert_401(resp, "GET /api/v1/dashboard/net-worth")


# ---------------------------------------------------------------------------
# Dashboards (CRUD)
# ---------------------------------------------------------------------------

class TestDashboardsCrudRequireAuth:
    def test_list_dashboards_requires_auth(self, client):
        resp = client.get("/api/v1/dashboards")
        _assert_401(resp, "GET /api/v1/dashboards")

    def test_create_dashboard_requires_auth(self, client):
        resp = client.post("/api/v1/dashboards", json={})
        _assert_401(resp, "POST /api/v1/dashboards")

    def test_get_dashboard_requires_auth(self, client, uid):
        resp = client.get(f"/api/v1/dashboards/{uid}")
        _assert_401(resp, f"GET /api/v1/dashboards/{uid}")

    def test_update_dashboard_requires_auth(self, client, uid):
        resp = client.put(f"/api/v1/dashboards/{uid}", json={})
        _assert_401(resp, f"PUT /api/v1/dashboards/{uid}")

    def test_delete_dashboard_requires_auth(self, client, uid):
        resp = client.delete(f"/api/v1/dashboards/{uid}")
        _assert_401(resp, f"DELETE /api/v1/dashboards/{uid}")


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettingsRequireAuth:
    def test_get_settings_requires_auth(self, client):
        resp = client.get("/api/v1/settings")
        _assert_401(resp, "GET /api/v1/settings")

    def test_update_setting_requires_auth(self, client):
        resp = client.put("/api/v1/settings/primary_currency", json={"value": "USD"})
        _assert_401(resp, "PUT /api/v1/settings/primary_currency")


# ---------------------------------------------------------------------------
# Exchange Rates (global data — still requires auth per spec)
# ---------------------------------------------------------------------------

class TestExchangeRatesRequireAuth:
    def test_list_exchange_rates_requires_auth(self, client):
        resp = client.get("/api/v1/exchange-rates")
        _assert_401(resp, "GET /api/v1/exchange-rates")


# ---------------------------------------------------------------------------
# Auth endpoints remain PUBLIC — should NOT return 401
# ---------------------------------------------------------------------------

class TestAuthEndpointsArePublic:
    def test_google_login_is_public(self, client):
        """POST /auth/google must be reachable without a token (returns 400, not 401)."""
        resp = client.post("/auth/google", json={})
        assert resp.status_code != 401, (
            "POST /auth/google should be public but returned 401"
        )

    def test_refresh_is_public(self, client):
        """POST /auth/refresh must be reachable without a token."""
        resp = client.post("/auth/refresh", json={})
        assert resp.status_code != 401

    def test_logout_is_public(self, client):
        """POST /auth/logout must be reachable without a token."""
        resp = client.post("/auth/logout", json={})
        assert resp.status_code != 401
