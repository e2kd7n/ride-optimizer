"""Tests for src/coverage_tracker.py — tile and road coverage tracking."""

import json
import math
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.coverage_tracker import (
    CoverageTracker,
    TileCoverage,
    lat_lon_to_tile,
    tile_to_bounds,
    _haversine_m,
    _interpolate_points,
    TILE_ZOOM,
)


# ── lat_lon_to_tile ──────────────────────────────────────────────

class TestLatLonToTile:
    def test_known_coordinate_nyc(self):
        x, y = lat_lon_to_tile(40.7128, -74.0060, zoom=14)
        assert isinstance(x, int) and isinstance(y, int)
        assert 4000 < x < 5000
        assert 5000 < y < 7000

    def test_known_coordinate_london(self):
        x, y = lat_lon_to_tile(51.5074, -0.1278, zoom=14)
        assert isinstance(x, int) and isinstance(y, int)

    def test_equator_prime_meridian(self):
        x, y = lat_lon_to_tile(0.0, 0.0, zoom=14)
        n = 2 ** 14
        assert x == n // 2
        assert y == n // 2

    def test_same_tile_for_nearby_points(self):
        t1 = lat_lon_to_tile(40.7128, -74.0060)
        t2 = lat_lon_to_tile(40.7130, -74.0058)
        assert t1 == t2

    def test_different_zoom_gives_different_tiles(self):
        t14 = lat_lon_to_tile(40.7128, -74.0060, zoom=14)
        t10 = lat_lon_to_tile(40.7128, -74.0060, zoom=10)
        assert t14 != t10


# ── tile_to_bounds ───────────────────────────────────────────────

class TestTileToBounds:
    def test_returns_four_floats(self):
        south, west, north, east = tile_to_bounds(8192, 8192)
        assert south < north
        assert west < east

    def test_round_trip(self):
        lat, lon = 40.7128, -74.0060
        x, y = lat_lon_to_tile(lat, lon)
        south, west, north, east = tile_to_bounds(x, y)
        assert south <= lat <= north
        assert west <= lon <= east

    def test_tile_size_zoom_14(self):
        south, west, north, east = tile_to_bounds(4825, 6160, zoom=14)
        lat_span = north - south
        lon_span = east - west
        assert 0.005 < lat_span < 0.025
        assert 0.01 < lon_span < 0.03


# ── _interpolate_points ─────────────────────────────────────────

class TestInterpolatePoints:
    def test_empty_returns_empty(self):
        assert _interpolate_points([]) == []

    def test_single_point(self):
        pts = [(40.0, -74.0)]
        assert _interpolate_points(pts) == pts

    def test_nearby_points_no_interpolation(self):
        pts = [(40.0, -74.0), (40.0001, -74.0001)]
        result = _interpolate_points(pts, interval_m=1000)
        assert len(result) == 2

    def test_distant_points_get_interpolated(self):
        pts = [(40.0, -74.0), (40.01, -74.0)]
        result = _interpolate_points(pts, interval_m=80)
        assert len(result) > 2
        assert result[0] == pts[0]
        assert result[-1] == pts[-1]

    def test_preserves_original_endpoints(self):
        pts = [(40.0, -74.0), (40.005, -74.005), (40.01, -74.01)]
        result = _interpolate_points(pts, interval_m=80)
        assert result[0] == pts[0]
        assert result[-1] == pts[-1]
        assert pts[1] in result


# ── _haversine_m ─────────────────────────────────────────────────

class TestHaversine:
    def test_same_point_is_zero(self):
        assert _haversine_m(40.0, -74.0, 40.0, -74.0) == 0.0

    def test_known_distance(self):
        dist = _haversine_m(40.7128, -74.0060, 40.7580, -73.9855)
        assert 4800 < dist < 5500


# ── TileCoverage dataclass ───────────────────────────────────────

class TestTileCoverage:
    def test_empty_coverage(self):
        tc = TileCoverage()
        assert tc.visited_count == 0
        assert tc.coverage_pct == 0.0

    def test_coverage_pct(self):
        tc = TileCoverage(
            visited={"1,2": {"first_ridden": "", "activity_ids": [1]}},
            total_in_bounds=4,
        )
        assert tc.visited_count == 1
        assert tc.coverage_pct == 25.0

    def test_to_dict(self):
        tc = TileCoverage(
            visited={"1,2": {"first_ridden": "2026-01-01", "activity_ids": [1]}},
            total_in_bounds=10,
            bounds=(40.0, -74.0, 41.0, -73.0),
            computed_at="2026-01-01T00:00:00",
        )
        d = tc.to_dict()
        assert d["visited_count"] == 1
        assert d["coverage_pct"] == 10.0
        assert d["bounds"] == (40.0, -74.0, 41.0, -73.0)


# ── CoverageTracker ─────────────────────────────────────────────

class TestCoverageTracker:
    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.get = MagicMock(side_effect=lambda key, default=None: default)
        return config

    @pytest.fixture
    def tracker(self, mock_config, tmp_path):
        t = CoverageTracker(mock_config)
        t.cache_dir = tmp_path
        return t

    def test_no_activities_empty_coverage(self, tracker):
        tracker._activities_cache = []
        result = tracker.get_tile_coverage_all()
        assert result.visited_count == 0

    def test_empty_polyline_skipped(self, tracker):
        tracker._activities_cache = [{"id": 1, "polyline": None}]
        result = tracker.get_tile_coverage_all()
        assert result.visited_count == 0

    def test_valid_activity_produces_tiles(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060), (40.7130, -74.0058)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [{
            "id": 1,
            "polyline": encoded,
            "start_date": "2026-01-01",
            "type": "Ride",
        }]
        result = tracker.get_tile_coverage_all()
        assert result.visited_count >= 1
        for key, meta in result.visited.items():
            assert 1 in meta["activity_ids"]

    def test_bounds_filter_excludes_outside(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060), (40.7130, -74.0058)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [{
            "id": 1,
            "polyline": encoded,
            "start_date": "2026-01-01",
            "type": "Ride",
        }]
        far_bounds = (10.0, 10.0, 11.0, 11.0)
        result = tracker.get_tile_coverage(far_bounds)
        assert result.visited_count == 0

    def test_bounds_filter_includes_inside(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060), (40.7130, -74.0058)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [{
            "id": 1,
            "polyline": encoded,
            "start_date": "2026-01-01",
            "type": "Ride",
        }]
        bounds = (40.0, -75.0, 41.0, -73.0)
        result = tracker.get_tile_coverage(bounds)
        assert result.visited_count >= 1

    def test_cache_write_and_read(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060), (40.7130, -74.0058)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [{
            "id": 1,
            "polyline": encoded,
            "start_date": "2026-01-01",
            "type": "Ride",
        }]
        bounds = (40.0, -75.0, 41.0, -73.0)
        r1 = tracker.get_tile_coverage(bounds)
        r2 = tracker.get_tile_coverage(bounds)
        assert r1.visited_count == r2.visited_count

    def test_invalidate_caches(self, tracker):
        cache_file = tracker.cache_dir / "coverage_tiles_test.json"
        cache_file.write_text("{}")
        tracker.invalidate_caches()
        assert not cache_file.exists()
        assert tracker._activities_cache is None

    def test_road_coverage_graceful_without_osmnx(self, tracker):
        tracker._activities_cache = []
        with patch.dict("sys.modules", {"osmnx": None, "shapely": None, "shapely.geometry": None, "shapely.strtree": None}):
            result = tracker.get_road_coverage((40.0, -74.0, 41.0, -73.0))
        assert result.get("status") == "error" or "osmnx" in result.get("message", "").lower() or "error" in result.get("status", "")

    def test_multiple_activities_same_tile(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [
            {"id": 1, "polyline": encoded, "start_date": "2026-01-01", "type": "Ride"},
            {"id": 2, "polyline": encoded, "start_date": "2026-01-02", "type": "Ride"},
        ]
        result = tracker.get_tile_coverage_all()
        for meta in result.visited.values():
            assert 1 in meta["activity_ids"]
            assert 2 in meta["activity_ids"]

    def test_missing_polyline_activity_skipped(self, tracker):
        tracker._activities_cache = [
            {"id": 1, "type": "Ride"},
            {"id": 2, "polyline": "", "type": "Ride"},
        ]
        result = tracker.get_tile_coverage_all()
        assert result.visited_count == 0
