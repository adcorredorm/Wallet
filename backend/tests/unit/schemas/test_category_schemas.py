"""Unit tests for Category Pydantic schemas."""
from uuid import uuid4
from datetime import datetime


class TestCategoryResponse:
    def test_response_includes_active_field(self):
        from app.schemas.category import CategoryResponse
        data = {
            "id": uuid4(), "name": "Alimentación", "type": "expense",
            "icon": None, "color": None, "parent_category_id": None,
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
            "active": True,
        }
        response = CategoryResponse(**data)
        assert "active" in response.model_dump()
        assert response.model_dump()["active"] is True

    def test_response_active_false(self):
        from app.schemas.category import CategoryResponse
        data = {
            "id": uuid4(), "name": "Archivada", "type": "expense",
            "icon": None, "color": None, "parent_category_id": None,
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
            "active": False,
        }
        assert CategoryResponse(**data).active is False


class TestCategoryUpdate:
    def test_update_accepts_active_true(self):
        from app.schemas.category import CategoryUpdate
        assert CategoryUpdate(active=True).active is True

    def test_update_accepts_active_false(self):
        from app.schemas.category import CategoryUpdate
        assert CategoryUpdate(active=False).active is False

    def test_update_active_defaults_to_none(self):
        from app.schemas.category import CategoryUpdate
        assert CategoryUpdate().active is None
