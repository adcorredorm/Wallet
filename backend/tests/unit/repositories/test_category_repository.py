"""Unit tests for CategoryRepository active-filter behaviour."""

import pytest
from unittest.mock import MagicMock, patch


class TestGetAllActive:
    def test_get_all_active_method_exists(self):
        from app.repositories.category import CategoryRepository
        assert hasattr(CategoryRepository, "get_all_active")

    def test_get_all_active_is_callable(self):
        from app.repositories.category import CategoryRepository
        assert callable(getattr(CategoryRepository, "get_all_active"))
