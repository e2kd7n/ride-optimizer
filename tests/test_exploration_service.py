"""Tests for app/services/exploration_service.py."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.exploration_service import ExplorationService
from src.coverage_tracker import TileCoverage


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get = MagicMock(side_effect=lambda key, default=None: default)
    return config


@pytest.fixture
def service(mock_config):
    return ExplorationService(mock_config)


class TestExplorationService:
    def test_get_tile_coverage_all_empty(self, service):
        service._tracker._activities_cache = []
        result = service.get_tile_coverage_all()
        assert result["status"] == "success"
        assert result["visited_count"] == 0

    def test_get_tile_coverage_bounded(self, service):
        service._tracker._activities_cache = []
        result = service.get_tile_coverage((40.0, -74.0, 41.0, -73.0))
        assert result["status"] == "success"
        assert result["visited_count"] == 0

    def test_get_tile_coverage_error_handling(self, service):
        with patch.object(service._tracker, "get_tile_coverage", side_effect=RuntimeError("boom")):
            result = service.get_tile_coverage((0, 0, 1, 1))
        assert result["status"] == "error"
        assert "boom" in result["message"]

    def test_invalidate_caches(self, service):
        with patch.object(service._tracker, "invalidate_caches") as mock_inv:
            service.invalidate_caches()
            mock_inv.assert_called_once()
