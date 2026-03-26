"""Tests for AuthService."""
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from app.services.auth import AuthService
from app.models.user import User


def auth_service_instance(app):
    """Return an AuthService bound to the current app context."""
    from app.services.auth import AuthService
    return AuthService()


def _hash_token_for_test(token_plain: str) -> str:
    """Mirror of auth._hash_token for use in tests."""
    import hashlib
    return hashlib.sha256(token_plain.encode()).hexdigest()


def test_grace_seconds_config(app):
    """REFRESH_TOKEN_GRACE_SECONDS must be set to 120 in all config classes."""
    with app.app_context():
        from flask import current_app
        assert current_app.config["REFRESH_TOKEN_GRACE_SECONDS"] == 120


def test_refresh_token_has_superseded_at_column(app):
    """RefreshToken model must have a superseded_at attribute defaulting to None."""
    with app.app_context():
        from app.models.refresh_token import RefreshToken
        from app.extensions import db
        from app.models.user import User

        user = User(google_id="sub_coltest", email="col@test.com", name="Col Test")
        db.session.add(user)
        db.session.commit()

        token = RefreshToken(
            user_id=user.id,
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(days=90),
        )
        db.session.add(token)
        db.session.commit()
        db.session.refresh(token)

        assert hasattr(token, "superseded_at")
        assert token.superseded_at is None


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
    """rotate_refresh_token issues new tokens; old token stays valid within grace window."""
    with app.app_context():
        user, _ = auth_service.find_or_create_user(
            {"sub": "sub888", "email": "b@c.com", "name": "B"}
        )
        tokens1 = auth_service.issue_tokens(user)
        tokens2 = auth_service.rotate_refresh_token(tokens1["refresh_token"])
        assert tokens2["refresh_token"] != tokens1["refresh_token"]
        # Old token is superseded but still accepted within grace window
        tokens3 = auth_service.rotate_refresh_token(tokens1["refresh_token"])
        assert "access_token" in tokens3
        assert "refresh_token" in tokens3


def test_revoke_refresh_token_is_idempotent(app, auth_service):
    """revoke_refresh_token does not raise if token does not exist."""
    with app.app_context():
        # Should not raise
        auth_service.revoke_refresh_token("nonexistent_token_string")


def test_rotate_refresh_token_sets_superseded_at(app):
    """rotate_refresh_token sets superseded_at on the old token instead of deleting it."""
    with app.app_context():
        from app.extensions import db
        from app.models.refresh_token import RefreshToken

        svc = auth_service_instance(app)
        user, _ = svc.find_or_create_user(
            {"sub": "sub_supersede", "email": "supersede@test.com", "name": "S"}
        )
        tokens1 = svc.issue_tokens(user)

        old_hash = _hash_token_for_test(tokens1["refresh_token"])

        tokens2 = svc.rotate_refresh_token(tokens1["refresh_token"])
        assert tokens2["refresh_token"] != tokens1["refresh_token"]

        # Old token must still exist but have superseded_at set
        old_token = db.session.execute(
            db.select(RefreshToken).where(RefreshToken.token_hash == old_hash)
        ).scalars().one_or_none()

        assert old_token is not None, "Old token row must not be deleted on rotation"
        assert old_token.superseded_at is not None, "superseded_at must be set"


def test_rotate_refresh_token_accepts_superseded_within_grace(app):
    """A superseded token reused within the grace window issues a fresh pair."""
    with app.app_context():
        svc = auth_service_instance(app)
        user, _ = svc.find_or_create_user(
            {"sub": "sub_grace", "email": "grace@test.com", "name": "G"}
        )
        tokens1 = svc.issue_tokens(user)

        # First rotation — normal
        svc.rotate_refresh_token(tokens1["refresh_token"])

        # Simulate: client never got tokens2, retries with tokens1 (within grace window)
        tokens3 = svc.rotate_refresh_token(tokens1["refresh_token"])
        assert "access_token" in tokens3
        assert "refresh_token" in tokens3
        assert tokens3["refresh_token"] != tokens1["refresh_token"]


def test_rotate_refresh_token_rejects_superseded_after_grace(app):
    """A superseded token reused after the grace window is rejected."""
    with app.app_context():
        from app.extensions import db
        from app.models.refresh_token import RefreshToken

        svc = auth_service_instance(app)
        user, _ = svc.find_or_create_user(
            {"sub": "sub_grace_expired", "email": "graceexp@test.com", "name": "GE"}
        )
        tokens1 = svc.issue_tokens(user)

        # Manually mark as superseded 3 minutes ago (past grace window)
        old_hash = _hash_token_for_test(tokens1["refresh_token"])
        old_token = db.session.execute(
            db.select(RefreshToken).where(RefreshToken.token_hash == old_hash)
        ).scalars().one()
        old_token.superseded_at = datetime.utcnow() - timedelta(seconds=180)
        db.session.commit()

        # Attempt to rotate with expired-grace superseded token
        with pytest.raises(Exception, match="inválido|expirado"):
            svc.rotate_refresh_token(tokens1["refresh_token"])


def test_issue_refresh_token_cleans_expired_grace_tokens(app):
    """issue_tokens (full_replace=True) deletes tokens past grace window."""
    with app.app_context():
        from app.extensions import db
        from app.models.refresh_token import RefreshToken

        svc = auth_service_instance(app)
        user, _ = svc.find_or_create_user(
            {"sub": "sub_cleanup", "email": "cleanup@test.com", "name": "Cleanup"}
        )

        # Manually insert a superseded token whose grace has expired (3 min ago)
        expired_token = RefreshToken(
            user_id=user.id,
            token_hash="b" * 64,
            expires_at=datetime.utcnow() + timedelta(days=90),
            superseded_at=datetime.utcnow() - timedelta(seconds=180),
        )
        db.session.add(expired_token)
        db.session.commit()
        expired_id = expired_token.id

        # issue_tokens uses full_replace=True — must delete ALL tokens including expired grace
        svc.issue_tokens(user)

        # Verify expired grace token was deleted
        still_there = db.session.get(RefreshToken, expired_id)
        assert still_there is None
