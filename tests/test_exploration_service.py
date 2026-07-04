"""Tests for app/services/exploration_service.py and src/ors_client.py."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.exploration_service import ExplorationService, _SURFACE_TO_PROFILE
from src.coverage_tracker import TileCoverage


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get = MagicMock(side_effect=lambda key, default=None: default)
    return config


@pytest.fixture
def service(mock_config):
    with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=mock_config):
        return ExplorationService()


@pytest.fixture
def service_with_key(mock_config):
    """Service pre-configured with a fake ORS API key."""
    def _get(key, default=None):
        if key == 'ors.api_key':
            return 'fake-key'
        return default

    mock_config.get = MagicMock(side_effect=_get)
    with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=mock_config):
        return ExplorationService()


# ── Existing coverage tests ──────────────────────────────────────


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


# ── Surface-preference → ORS profile mapping ────────────────────


class TestSurfaceProfileMapping:
    @pytest.mark.parametrize("pref,expected", [
        ("any", "cycling-regular"),
        ("paved", "cycling-road"),
        ("unpaved", "cycling-mountain"),
    ])
    def test_surface_to_profile(self, pref, expected):
        assert _SURFACE_TO_PROFILE[pref] == expected


# ── ORS proxy: success / failure / timeout / 429 ─────────────────


class TestOrsClient:
    """Tests for src/ors_client.get_route using mocked requests.post."""

    def _sample_ors_response(self):
        return {
            "features": [{
                "geometry": {
                    "coordinates": [[-87.65, 41.98], [-87.64, 41.99], [-87.65, 41.98]],
                },
                "properties": {
                    "summary": {"distance": 5000.0, "duration": 1200.0},
                    "extras": {
                        "surface": {
                            "values": [[0, 1, 1], [1, 2, 1], [2, 3, 9]],
                        }
                    },
                },
            }],
        }

    def test_success(self):
        from src import ors_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self._sample_ors_response()
        mock_response.raise_for_status = MagicMock()

        with patch("src.ors_client.requests.post", return_value=mock_response) as mock_post:
            result = ors_client.get_route([[41.98, -87.65], [41.99, -87.64]], "cycling-regular", api_key="k")
        assert result is not None
        assert "features" in result
        mock_post.assert_called_once()

    def test_no_api_key_returns_none(self):
        from src import ors_client

        with patch("src.ors_client.requests.post") as mock_post:
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="")
        assert result is None
        mock_post.assert_not_called()

    def test_timeout_returns_none(self):
        from src import ors_client

        with patch("src.ors_client.requests.post", side_effect=requests.exceptions.Timeout()):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")
        assert result is None

    def test_network_error_returns_none(self):
        from src import ors_client

        with patch("src.ors_client.requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")
        assert result is None

    def test_http_429_returns_rate_limited_sentinel(self):
        from src import ors_client

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("src.ors_client.requests.post", return_value=mock_response):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")
        assert result is not None
        assert result.get("_ors_rate_limited") is True


# ── compute_route: no API key ────────────────────────────────────


class TestComputeRoute:
    def test_no_api_key_returns_error(self, service):
        """compute_route without an API key returns a clear error, does not crash."""
        result = service.compute_route([[41.0, -87.0], [41.1, -87.1]])
        assert result["status"] == "error"
        assert "not configured" in result["message"]

    def test_success_parses_response(self, service_with_key):
        """compute_route returns coordinates, distance_km, duration_min, surface_breakdown."""
        raw = {
            "features": [{
                "geometry": {
                    "coordinates": [[-87.65, 41.98], [-87.64, 41.99], [-87.65, 41.98]],
                },
                "properties": {
                    "summary": {"distance": 12345.0, "duration": 3600.0},
                    "extras": {
                        "surface": {
                            "values": [[0, 1, 1], [1, 2, 1], [2, 3, 9]],
                        }
                    },
                },
            }],
        }
        with patch("src.ors_client.get_route", return_value=raw):
            result = service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])

        assert result["status"] == "success"
        assert result["distance_km"] == round(12345.0 / 1000, 2)
        assert result["duration_min"] == round(3600.0 / 60, 1)
        # Coordinates are flipped from [lon, lat] to [lat, lon]
        assert result["coordinates"][0] == [41.98, -87.65]
        sb = result["surface_breakdown"]
        assert "paved_pct" in sb
        assert "unpaved_pct" in sb
        assert "unknown_pct" in sb

    def test_rate_limited_returns_error(self, service_with_key):
        with patch("src.ors_client.get_route", return_value={"_ors_rate_limited": True}):
            result = service_with_key.compute_route([[0, 0], [1, 1]])
        assert result["status"] == "error"
        assert "rate limit" in result["message"].lower()

    def test_ors_failure_returns_error(self, service_with_key):
        with patch("src.ors_client.get_route", return_value=None):
            result = service_with_key.compute_route([[0, 0], [1, 1]])
        assert result["status"] == "error"

    def test_memoization_within_ttl(self, service_with_key):
        """A second identical (waypoints, profile) request within TTL does not call ORS again."""
        raw = {
            "features": [{
                "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
                "properties": {
                    "summary": {"distance": 1000.0, "duration": 300.0},
                    "extras": {},
                },
            }],
        }
        with patch("src.ors_client.get_route", return_value=raw) as mock_get:
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
        assert mock_get.call_count == 1

    def test_memoization_expired(self, service_with_key):
        """After TTL expires the cache misses and ORS is called again."""
        raw = {
            "features": [{
                "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
                "properties": {
                    "summary": {"distance": 1000.0, "duration": 300.0},
                    "extras": {},
                },
            }],
        }
        with patch("src.ors_client.get_route", return_value=raw) as mock_get:
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
            # Manually expire all cache entries.
            for k in service_with_key._route_cache:
                result, _ = service_with_key._route_cache[k]
                service_with_key._route_cache[k] = (result, time.monotonic() - 1)
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
        assert mock_get.call_count == 2


# ── surface_breakdown reduction ──────────────────────────────────


class TestReduceSurfaceExtras:
    def test_mixed_surfaces(self):
        extras = {
            "surface": {
                "values": [
                    [0, 1, 1],   # paved (value 1)
                    [1, 2, 1],   # paved
                    [2, 3, 9],   # unpaved (value 9)
                    [3, 4, 99],  # unknown
                ]
            }
        }
        sb = ExplorationService._reduce_surface_extras(extras, 4000.0)
        assert sb["paved_pct"] == 50
        assert sb["unpaved_pct"] == 25
        assert sb["unknown_pct"] == 25

    def test_empty_extras(self):
        sb = ExplorationService._reduce_surface_extras({}, 1000.0)
        assert sb == {"paved_pct": 0, "unpaved_pct": 0, "unknown_pct": 100}

    def test_zero_total_distance(self):
        """Does not divide by zero when total_distance_m is 0."""
        extras = {"surface": {"values": [[0, 1, 1]]}}
        sb = ExplorationService._reduce_surface_extras(extras, 0.0)
        assert sb == {"paved_pct": 0, "unpaved_pct": 0, "unknown_pct": 100}
