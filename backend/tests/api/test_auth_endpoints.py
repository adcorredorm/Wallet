"""Integration tests for /auth/* endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from app.models.user import User


@pytest.fixture
def mock_google_verify(app):
    """Patch AuthService.verify_google_token to return a fake payload."""
    with patch("app.api.auth.auth_service.verify_google_token") as mock:
        mock.return_value = {
            "sub": "google_sub_test",
            "email": "test@example.com",
            "name": "Test User",
        }
        yield mock


def test_post_auth_google_creates_user(client, mock_google_verify):
    """POST /auth/google creates user and returns tokens."""
    resp = client.post(
        "/auth/google",
        json={"id_token": "fake_google_token"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["is_new_user"] is True


def test_post_auth_google_missing_id_token(client):
    """POST /auth/google returns 400 when id_token is absent."""
    resp = client.post("/auth/google", json={})
    assert resp.status_code == 400


def test_post_auth_refresh_rotates_token(client, mock_google_verify):
    """POST /auth/refresh returns new tokens and invalidates old refresh token."""
    # First login
    login_resp = client.post(
        "/auth/google",
        json={"id_token": "fake_google_token"},
    )
    old_refresh = login_resp.get_json()["data"]["refresh_token"]

    # Refresh
    refresh_resp = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.get_json()["data"]
    assert "access_token" in new_data
    assert new_data["refresh_token"] != old_refresh


def test_post_auth_refresh_invalid_token_returns_401(client):
    """POST /auth/refresh returns 401 for unknown refresh token."""
    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": "completely_fake_token"},
    )
    assert resp.status_code == 401


def test_post_auth_logout_returns_204(client, mock_google_verify):
    """POST /auth/logout deletes the refresh token and returns 204."""
    login_resp = client.post(
        "/auth/google",
        json={"id_token": "fake_google_token"},
    )
    refresh_token = login_resp.get_json()["data"]["refresh_token"]

    logout_resp = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204


def test_post_auth_logout_is_idempotent(client):
    """POST /auth/logout returns 204 even if token does not exist."""
    resp = client.post(
        "/auth/logout",
        json={"refresh_token": "nonexistent_token"},
    )
    assert resp.status_code == 204
