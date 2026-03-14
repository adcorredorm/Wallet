"""Integration tests: cursor-based incremental sync on GET endpoints.

These tests verify that all list GET endpoints:
- Return 200 + X-Sync-Cursor header when no cursor is provided (full sync mode)
- Return 304 + X-Sync-Cursor + empty body when a future cursor is provided
  (nothing changed since the cursor timestamp)
- Return 200 + flat list when a past cursor is provided (incremental mode)
- Treat invalid cursors as absent (full sync fallback)
"""

import json
import base64
from datetime import datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# Cursor helpers
# ---------------------------------------------------------------------------

def _cursor(dt: datetime) -> str:
    """Encode a datetime into an opaque base64url cursor string."""
    payload = json.dumps({"t": dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z", "v": 1})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def future_cursor() -> str:
    """Return a cursor timestamped 1 hour in the future."""
    return _cursor(datetime.utcnow() + timedelta(hours=1))


def past_cursor() -> str:
    """Return a cursor timestamped 1 hour in the past."""
    return _cursor(datetime.utcnow() - timedelta(hours=1))


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

def test_accounts_no_cursor_returns_200_and_cursor(client, make_account):
    """Full sync: no cursor -> 200 with X-Sync-Cursor header."""
    make_account()
    r = client.get("/api/v1/accounts")
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


def test_accounts_future_cursor_304(client, make_account):
    """Future cursor -> 304 with new cursor, empty body."""
    make_account()
    old = future_cursor()
    r = client.get("/api/v1/accounts", headers={"If-Sync-Cursor": old})
    assert r.status_code == 304
    assert r.data == b""
    assert r.headers.get("X-Sync-Cursor") != old  # always a freshly-encoded cursor


def test_accounts_past_cursor_returns_flat_list(client, make_account):
    """Past cursor -> 200 with flat list of changed accounts."""
    make_account()
    r = client.get("/api/v1/accounts", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def test_transactions_no_cursor_returns_200_and_cursor(client, make_transaction):
    """Full sync: no cursor -> 200 with X-Sync-Cursor header."""
    make_transaction()
    r = client.get("/api/v1/transactions")
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


def test_transactions_no_cursor_returns_paginated(client, make_transaction):
    """Without cursor, transactions returns paginated wrapper."""
    make_transaction()
    r = client.get("/api/v1/transactions")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "items" in body["data"]


def test_transactions_future_cursor_304(client, make_transaction):
    """Future cursor -> 304 with empty body."""
    make_transaction()
    r = client.get("/api/v1/transactions", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304
    assert r.data == b""
    assert "X-Sync-Cursor" in r.headers


def test_transactions_past_cursor_returns_flat_list(client, make_transaction):
    """With past cursor, response is flat list — not paginated wrapper."""
    make_transaction()
    r = client.get("/api/v1/transactions", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# Transfers
# ---------------------------------------------------------------------------

def test_transfers_no_cursor_returns_200_and_cursor(client, make_transfer):
    """Full sync: no cursor -> 200 with X-Sync-Cursor header."""
    make_transfer()
    r = client.get("/api/v1/transfers")
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


def test_transfers_future_cursor_304(client, make_transfer):
    """Future cursor -> 304."""
    make_transfer()
    r = client.get("/api/v1/transfers", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304
    assert r.data == b""
    assert "X-Sync-Cursor" in r.headers


def test_transfers_past_cursor_returns_flat_list(client, make_transfer):
    """Past cursor -> 200 with flat list."""
    make_transfer()
    r = client.get("/api/v1/transfers", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def test_categories_no_cursor_returns_200_and_cursor(client, make_category):
    """Full sync: no cursor -> 200 with X-Sync-Cursor header."""
    make_category()
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


def test_categories_future_cursor_304(client, make_category):
    """Future cursor -> 304."""
    make_category()
    r = client.get("/api/v1/categories", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304
    assert r.data == b""
    assert "X-Sync-Cursor" in r.headers


def test_categories_past_cursor_returns_flat_list(client, make_category):
    """Past cursor -> 200 with flat list."""
    make_category()
    r = client.get("/api/v1/categories", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------

def test_dashboards_no_cursor_returns_200_and_cursor(client, make_dashboard):
    """Full sync: no cursor -> 200 with X-Sync-Cursor header."""
    make_dashboard()
    r = client.get("/api/v1/dashboards")
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


def test_dashboards_future_cursor_304(client, make_dashboard):
    """Future cursor -> 304."""
    make_dashboard()
    r = client.get("/api/v1/dashboards", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304
    assert r.data == b""
    assert "X-Sync-Cursor" in r.headers


def test_dashboards_past_cursor_returns_flat_list(client, make_dashboard):
    """Past cursor -> 200 with flat list."""
    make_dashboard()
    r = client.get("/api/v1/dashboards", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# Exchange rates
# ---------------------------------------------------------------------------

def test_exchange_rates_no_cursor_returns_200_and_cursor(client, make_exchange_rate):
    """Full sync: no cursor -> 200 with X-Sync-Cursor header."""
    make_exchange_rate()
    r = client.get("/api/v1/exchange-rates")
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


def test_exchange_rates_future_cursor_304(client, make_exchange_rate):
    """Future cursor -> 304."""
    make_exchange_rate()
    r = client.get("/api/v1/exchange-rates", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304
    assert r.data == b""
    assert "X-Sync-Cursor" in r.headers


def test_exchange_rates_past_cursor_returns_flat_list(client, make_exchange_rate):
    """With past cursor, exchange-rates returns flat list (not {rates, last_updated} wrapper)."""
    make_exchange_rate()
    r = client.get("/api/v1/exchange-rates", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_invalid_cursor_treated_as_no_cursor(client, make_account):
    """Invalid cursor is silently ignored — treated as full sync."""
    make_account()
    r = client.get("/api/v1/accounts", headers={"If-Sync-Cursor": "invalid!!!"})
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


def test_empty_db_no_cursor_returns_200(client):
    """Empty DB with no cursor -> 200 (not 304)."""
    r = client.get("/api/v1/accounts")
    assert r.status_code == 200
