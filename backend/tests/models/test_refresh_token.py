"""Tests for the RefreshToken model."""
from app.models.refresh_token import RefreshToken


def test_refresh_token_has_expected_columns(app):
    columns = {c.name for c in RefreshToken.__table__.columns}
    assert {"id", "user_id", "token_hash", "expires_at", "created_at"}.issubset(columns)


def test_refresh_token_has_no_revoked_at(app):
    """RefreshToken must NOT have a revoked_at column — rows are physically deleted."""
    columns = {c.name for c in RefreshToken.__table__.columns}
    assert "revoked_at" not in columns


def test_refresh_token_user_id_fk(app):
    fk_cols = {fk.column.table.name for fk in RefreshToken.__table__.foreign_keys}
    assert "users" in fk_cols


def test_refresh_token_repr(app):
    import uuid
    rt = RefreshToken(user_id=uuid.uuid4(), token_hash="abc123def456")
    assert "abc123" in repr(rt)
