"""Tests for AuthService."""
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from app.services.auth import AuthService
from app.models.user import User


@pytest.fixture
def auth_service(app):
    return AuthService()


@pytest.fixture
def mock_google_payload():
    return {
        "sub": "google_sub_12345",
        "email": "user@example.com",
        "name": "Test User",
    }


def test_find_or_create_user_creates_new_user(app, auth_service, mock_google_payload):
    """find_or_create_user creates a new User when google_id is unknown."""
    with app.app_context():
        user, is_new = auth_service.find_or_create_user(mock_google_payload)
        assert is_new is True
        assert user.google_id == "google_sub_12345"
        assert user.email == "user@example.com"


def test_find_or_create_user_finds_existing_user(app, auth_service, mock_google_payload):
    """find_or_create_user returns existing user on second call."""
    with app.app_context():
        user1, is_new1 = auth_service.find_or_create_user(mock_google_payload)
        user2, is_new2 = auth_service.find_or_create_user(mock_google_payload)
        assert is_new2 is False
        assert user1.id == user2.id


def test_issue_tokens_returns_access_and_refresh(app, auth_service):
    """issue_tokens returns a dict with access_token and refresh_token."""
    with app.app_context():
        user, _ = auth_service.find_or_create_user(
            {"sub": "sub999", "email": "a@b.com", "name": "A"}
        )
        tokens = auth_service.issue_tokens(user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens


def test_rotate_refresh_token_returns_new_tokens(app, auth_service):
    """rotate_refresh_token issues new tokens and invalidates the old one."""
    with app.app_context():
        user, _ = auth_service.find_or_create_user(
            {"sub": "sub888", "email": "b@c.com", "name": "B"}
        )
        tokens1 = auth_service.issue_tokens(user)
        tokens2 = auth_service.rotate_refresh_token(tokens1["refresh_token"])
        assert tokens2["refresh_token"] != tokens1["refresh_token"]
        # Old token should no longer be valid
        with pytest.raises(Exception):
            auth_service.rotate_refresh_token(tokens1["refresh_token"])


def test_revoke_refresh_token_is_idempotent(app, auth_service):
    """revoke_refresh_token does not raise if token does not exist."""
    with app.app_context():
        # Should not raise
        auth_service.revoke_refresh_token("nonexistent_token_string")
