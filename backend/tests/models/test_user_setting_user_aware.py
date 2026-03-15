"""Tests verifying UserSetting has composite PK (user_id, key)."""
from app.models.user_setting import UserSetting


def test_user_setting_pk_is_composite(app):
    """UserSetting PK must include user_id and key."""
    pk_cols = {col.name for col in UserSetting.__table__.primary_key}
    assert pk_cols == {"user_id", "key"}


def test_user_setting_user_id_fk(app):
    fk_tables = {fk.column.table.name for fk in UserSetting.__table__.foreign_keys}
    assert "users" in fk_tables


def test_user_setting_has_no_id_column(app):
    """UserSetting does not inherit from BaseModel — no UUID id column."""
    columns = {c.name for c in UserSetting.__table__.columns}
    assert "id" not in columns


def test_user_setting_has_no_client_id_column(app):
    """UserSetting has no client_id — it is not an offline-first sync model."""
    columns = {c.name for c in UserSetting.__table__.columns}
    assert "client_id" not in columns
