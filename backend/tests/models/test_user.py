"""Tests for the User model."""
import pytest
from uuid import UUID
from app.models.user import User


def test_user_has_expected_columns(app):
    """User table has id, google_id, email, name, created_at, updated_at."""
    columns = {c.name for c in User.__table__.columns}
    assert {"id", "google_id", "email", "name", "created_at", "updated_at"}.issubset(columns)


def test_user_repr(app):
    u = User(google_id="sub123", email="test@example.com", name="Test")
    assert "test@example.com" in repr(u)
