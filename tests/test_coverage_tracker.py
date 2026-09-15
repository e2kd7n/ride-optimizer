"""Tests for src/coverage_tracker.py — tile and road coverage tracking."""

import json
import math
import os
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests

from src.coverage_tracker import (
    CoverageTracker,
    TileCoverage,
    lat_lon_to_tile,
    tile_to_bounds,
    _bbox_cache_key,
    _snap_bbox_to_grid,
    _WATER_POLYGON_GRID_DEGREES,
    _segment_tiles,
    _activity_tiles,
    _robust_tile_range,
    TILE_ZOOM,
    SQUADRATINHO_ZOOM,
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


# ── _segment_tiles / _activity_tiles (grid traversal) ────────────

class TestSegmentTiles:
    def test_same_tile_returns_single_tile(self):
        tiles = _segment_tiles(40.0, -74.0, 40.0001, -74.0001, TILE_ZOOM)
        assert tiles == [lat_lon_to_tile(40.0, -74.0, TILE_ZOOM)]

    def test_endpoints_match_lat_lon_to_tile(self):
        tiles = _segment_tiles(40.7, -74.05, 40.7, -73.95, SQUADRATINHO_ZOOM)
        assert tiles[0] == lat_lon_to_tile(40.7, -74.05, SQUADRATINHO_ZOOM)
        assert tiles[-1] == lat_lon_to_tile(40.7, -73.95, SQUADRATINHO_ZOOM)

    def test_path_is_four_connected(self):
        """No diagonal jumps — every step must share an edge with the last
        (otherwise a tile the line actually crosses would be skipped)."""
        tiles = _segment_tiles(40.5, -74.1, 40.9, -73.7, SQUADRATINHO_ZOOM)
        assert len(tiles) > 1
        for prev, curr in zip(tiles, tiles[1:]):
            dx = abs(curr[0] - prev[0])
            dy = abs(curr[1] - prev[1])
            assert dx + dy == 1

    def test_vertical_segment_stays_in_one_column(self):
        tiles = _segment_tiles(40.5, -74.0, 40.9, -74.0, SQUADRATINHO_ZOOM)
        assert all(t[0] == tiles[0][0] for t in tiles)

    def test_zoom_affects_tile_count(self):
        coarse = _segment_tiles(40.5, -74.1, 40.9, -73.7, TILE_ZOOM)
        fine = _segment_tiles(40.5, -74.1, 40.9, -73.7, SQUADRATINHO_ZOOM)
        assert len(fine) > len(coarse)


class TestActivityTiles:
    def test_empty_coords(self):
        assert _activity_tiles([], TILE_ZOOM) == set()

    def test_single_point(self):
        tiles = _activity_tiles([(40.0, -74.0)], TILE_ZOOM)
        assert tiles == {lat_lon_to_tile(40.0, -74.0, TILE_ZOOM)}

    def test_multi_point_covers_all_segments(self):
        coords = [(40.0, -74.0), (40.01, -74.0), (40.01, -73.99)]
        tiles = _activity_tiles(coords, TILE_ZOOM)
        for lat, lon in coords:
            assert lat_lon_to_tile(lat, lon, TILE_ZOOM) in tiles


# ── CoverageTracker.tiles_crossed_by_path (#493) ──────────────────

class TestTilesCrossedByPath:
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

    def test_matches_activity_tiles(self, tracker):
        coords = [(40.5, -74.1), (40.6, -74.0), (40.7, -73.9)]
        assert tracker.tiles_crossed_by_path(coords, TILE_ZOOM) == _activity_tiles(coords, TILE_ZOOM)

    def test_empty_path(self, tracker):
        assert tracker.tiles_crossed_by_path([], TILE_ZOOM) == set()

    def test_single_point(self, tracker):
        result = tracker.tiles_crossed_by_path([(40.0, -74.0)], TILE_ZOOM)
        assert result == {lat_lon_to_tile(40.0, -74.0, TILE_ZOOM)}

    def test_road_route_boundary_never_enters_tile(self, tracker):
        """Regression for #493: a route that hugs a tile's boundary edge
        (e.g. a road running along a section line) must NOT be reported as
        crossing the adjacent tile just because it runs close to it."""
        x, y = 4825, 6160
        south, west, north, east = tile_to_bounds(x, y, zoom=TILE_ZOOM)
        tile_width = east - west

        # Path runs just outside the tile's west edge (in the neighbouring
        # tile) — this is the "road along the section line" case from the
        # bug report: geometrically close, but never actually inside.
        just_outside_lon = west - tile_width * 0.001
        outside_path = [(south, just_outside_lon), (north, just_outside_lon)]
        crossed = tracker.tiles_crossed_by_path(outside_path, TILE_ZOOM)
        assert (x, y) not in crossed

        # A path that actually dips into the tile's interior does enter it.
        inside_lon = west + tile_width * 0.5
        inside_path = [(south, inside_lon), (north, inside_lon)]
        crossed_interior = tracker.tiles_crossed_by_path(inside_path, TILE_ZOOM)
        assert (x, y) in crossed_interior


# ── TileCoverage dataclass ───────────────────────────────────────

class TestTileCoverage:
    def test_empty_coverage(self):
        tc = TileCoverage()
        assert tc.visited_count == 0
        assert tc.coverage_pct == 0.0

    def test_coverage_pct(self):
        # #579: visited values are a trimmed placeholder, not per-tile detail.
        tc = TileCoverage(
            visited={"1,2": 1},
            total_in_bounds=4,
        )
        assert tc.visited_count == 1
        assert tc.coverage_pct == 25.0

    def test_to_dict(self):
        tc = TileCoverage(
            visited={"1,2": 1},
            total_in_bounds=10,
            bounds=(40.0, -74.0, 41.0, -73.0),
            computed_at="2026-01-01T00:00:00",
        )
        d = tc.to_dict()
        assert d["visited_count"] == 1
        assert d["coverage_pct"] == 10.0
        assert d["bounds"] == (40.0, -74.0, 41.0, -73.0)

    def test_coverage_pct_caps_at_100(self):
        """#556: get_tile_coverage_all() trims outlier tiles out of
        total_in_bounds while keeping them in `visited`, which can push the
        raw ratio above 100%. Capped rather than shown as nonsensical."""
        tc = TileCoverage(
            visited={f"{i},0": 1 for i in range(10)},
            total_in_bounds=5,
        )
        assert tc.coverage_pct == 100.0


# ── _robust_tile_range (#556) ──────────────────────────────────────

class TestRobustTileRange:
    """A single geographically-distant activity (a trip, or a corrupted GPS
    point) shouldn't balloon get_tile_coverage_all()'s reported bounds to span
    the outlier — verified on production data: 5,849 visited tiles produced a
    bounding box spanning nearly the whole globe (69.6M total_in_bounds,
    permanent ~0.0% coverage_pct)."""

    def test_small_sample_uses_raw_min_max(self):
        """Below _OUTLIER_MIN_SAMPLES, trimming is skipped entirely — not
        enough points to trust percentile statistics."""
        assert _robust_tile_range([10, 11, 12, 1000]) == (10, 1000)

    def test_large_cluster_trims_far_outlier(self):
        cluster = list(range(100, 150))  # 50 tightly-packed points
        coords = cluster + [50000]  # one wild outlier, 31st+ point
        min_v, max_v = _robust_tile_range(coords)
        assert (min_v, max_v) == (100, 149)

    def test_large_cluster_trims_outlier_on_either_side(self):
        cluster = list(range(1000, 1050))
        coords = [-99999] + cluster + [99999]
        min_v, max_v = _robust_tile_range(coords)
        assert (min_v, max_v) == (1000, 1049)

    def test_uniform_values_zero_iqr_no_crash(self):
        """All-identical values (zero spread) can't have outliers by
        definition — must not divide by zero or otherwise error."""
        assert _robust_tile_range([5] * 25) == (5, 5)

    def test_no_outliers_returns_raw_min_max(self):
        coords = list(range(200, 240))
        assert _robust_tile_range(coords) == (200, 239)


class TestGetTileCoverageAllOutlierBounds:
    """Integration-level: get_tile_coverage_all() end to end with a synthetic
    tile index reproducing the production scenario."""

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

    def test_outlier_tile_does_not_balloon_bounds(self, tracker):
        zoom = TILE_ZOOM
        tiles = {
            f"{4825 + i},{6160 + i % 5}": {"first_ridden": "2026-01-01", "activity_ids": [1]}
            for i in range(30)
        }
        outlier_key = "100,9000"  # a tile from the other side of the world
        tiles[outlier_key] = {"first_ridden": "2026-02-01", "activity_ids": [2]}

        # Seed the persisted tile index directly rather than synthesizing a
        # real cross-globe polyline — _build_or_update_tile_index() only
        # re-decodes activities whose id isn't already in indexed_activity_ids.
        tracker._tile_index_cache[zoom] = {
            "indexed_activity_ids": {1, 2},
            "tiles": tiles,
        }
        tracker._activities_cache = []

        result = tracker.get_tile_coverage_all(zoom=zoom)

        # The outlier tile is still reported as visited (real progress, still
        # shown on the map)...
        assert outlier_key in result.visited
        assert result.visited_count == 31
        # ...but no longer blows up the reported bounding box.
        assert result.total_in_bounds < 1000
        assert result.coverage_pct <= 100.0

    def test_no_outliers_bounds_unaffected(self, tracker):
        """A tight, outlier-free cluster gets the same bounds as before."""
        zoom = TILE_ZOOM
        tiles = {
            f"{4825 + i},{6160 + i % 5}": {"first_ridden": "2026-01-01", "activity_ids": [1]}
            for i in range(30)
        }
        tracker._tile_index_cache[zoom] = {
            "indexed_activity_ids": {1},
            "tiles": tiles,
        }
        tracker._activities_cache = []

        result = tracker.get_tile_coverage_all(zoom=zoom)

        assert result.visited_count == 30
        assert result.total_in_bounds == 30 * 5  # 30 x-values x 5 y-values


# ── trimmed per-tile response payload (#579) ──────────────────────

class TestTrimmedTileCoverageResponse:
    """The frontend (exploration-worker.js, explore.js's drawTileGrid) only
    ever reads Object.keys(coverageData.visited) — per-tile
    first_ridden/activity_ids detail was shipped over the wire and
    silently discarded on every request, several MB of wasted payload at
    full-history scale. Response-building trims tile values to a
    placeholder; the tile index itself keeps full detail for incremental
    updates."""

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

    @staticmethod
    def _activity(act_id, coords, date="2026-01-01"):
        import polyline as codec
        return {"id": act_id, "polyline": codec.encode(coords), "start_date": date, "type": "Ride"}

    def test_get_tile_coverage_all_trims_per_tile_detail(self, tracker):
        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        result = tracker.get_tile_coverage_all()
        assert result.visited_count >= 1
        for value in result.visited.values():
            assert not isinstance(value, dict)

    def test_get_tile_coverage_trims_per_tile_detail(self, tracker):
        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        bounds = (40.0, -75.0, 41.0, -73.0)
        result = tracker.get_tile_coverage(bounds)
        assert result.visited_count >= 1
        for value in result.visited.values():
            assert not isinstance(value, dict)

    def test_internal_tile_index_retains_full_detail(self, tracker):
        """The trim applies only to the response-building path — the
        on-disk/in-memory tile index still needs first_ridden/activity_ids
        for incremental updates and cross-activity dedup."""
        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        tracker.get_tile_coverage_all()
        index = tracker._tile_index_cache[TILE_ZOOM]
        assert index["tiles"]
        for meta in index["tiles"].values():
            assert "first_ridden" in meta
            assert "activity_ids" in meta


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
        # Response values are trimmed (#579) — the underlying tile index
        # still tracks which activities touched each tile.
        index = tracker._tile_index_cache[TILE_ZOOM]
        for key, meta in index["tiles"].items():
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

    def test_squadratinho_zoom_produces_finer_grid(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060), (40.72, -74.0), (40.73, -73.99)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [{
            "id": 1, "polyline": encoded, "start_date": "2026-01-01", "type": "Ride",
        }]
        squadrat = tracker.get_tile_coverage_all(zoom=TILE_ZOOM)
        squadratinho = tracker.get_tile_coverage_all(zoom=SQUADRATINHO_ZOOM)
        assert squadratinho.zoom == SQUADRATINHO_ZOOM
        assert squadrat.zoom == TILE_ZOOM
        assert squadratinho.visited_count > squadrat.visited_count

    def test_zoom_uses_separate_cache_entries(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060), (40.7130, -74.0058)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [{
            "id": 1, "polyline": encoded, "start_date": "2026-01-01", "type": "Ride",
        }]
        bounds = (40.0, -75.0, 41.0, -73.0)
        tracker.get_tile_coverage(bounds, zoom=TILE_ZOOM)
        tracker.get_tile_coverage(bounds, zoom=SQUADRATINHO_ZOOM)
        cache_files = list(tracker.cache_dir.glob("tile_index_*.json"))
        assert len(cache_files) == 2

    def test_invalidate_caches_is_soft(self, tracker):
        """#571: the automatic post-sync path (invalidate_caches()) must
        clear in-memory state without deleting the on-disk tile index —
        otherwise every nightly sync forces a full cold rebuild."""
        cache_file = tracker.cache_dir / "tile_index_14.json"
        cache_file.write_text('{"indexed_activity_ids": [], "tiles": {}}')
        tracker._tile_index_cache[14] = {"indexed_activity_ids": set(), "tiles": {}}
        tracker._activities_cache = [{"id": 1, "type": "Ride"}]

        tracker.invalidate_caches()

        assert cache_file.exists()  # on-disk index NOT deleted
        assert tracker._activities_cache is None  # #583: activities cache cleared too
        assert tracker._tile_index_cache == {}

    def test_hard_invalidate_caches_removes_on_disk_index(self, tracker):
        cache_file = tracker.cache_dir / "tile_index_14.json"
        cache_file.write_text('{"indexed_activity_ids": [], "tiles": {}}')
        tracker._tile_index_cache[14] = {"indexed_activity_ids": set(), "tiles": {}}
        tracker.hard_invalidate_caches()
        assert not cache_file.exists()
        assert tracker._activities_cache is None
        assert tracker._tile_index_cache == {}

    def test_multiple_activities_same_tile(self, tracker):
        import polyline as codec
        coords = [(40.7128, -74.0060)]
        encoded = codec.encode(coords)
        tracker._activities_cache = [
            {"id": 1, "polyline": encoded, "start_date": "2026-01-01", "type": "Ride"},
            {"id": 2, "polyline": encoded, "start_date": "2026-01-02", "type": "Ride"},
        ]
        result = tracker.get_tile_coverage_all()
        assert result.visited_count >= 1
        # Response values are trimmed (#579) — the underlying tile index
        # still tracks which activities touched each tile.
        index = tracker._tile_index_cache[TILE_ZOOM]
        for meta in index["tiles"].values():
            assert 1 in meta["activity_ids"]
            assert 2 in meta["activity_ids"]

    def test_missing_polyline_activity_skipped(self, tracker):
        tracker._activities_cache = [
            {"id": 1, "type": "Ride"},
            {"id": 2, "polyline": "", "type": "Ride"},
        ]
        result = tracker.get_tile_coverage_all()
        assert result.visited_count == 0


# ── Tile index incremental build/update (perf rewrite) ───────────

class TestTileIndex:
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

    @staticmethod
    def _activity(act_id, coords, date="2026-01-01"):
        import polyline as codec
        return {"id": act_id, "polyline": codec.encode(coords), "start_date": date, "type": "Ride"}

    def test_incremental_update_only_decodes_new_activities(self, tracker):
        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        tracker.get_tile_coverage_all()  # first build indexes activity 1

        a2 = self._activity(2, [(41.0, -75.0), (41.001, -75.001)])
        tracker._activities_cache = [a1, a2]
        with patch.object(tracker, "_decode_activity_coords", wraps=tracker._decode_activity_coords) as spy:
            tracker.get_tile_coverage_all()
            # Only the new activity (id=2) should be decoded on the second call.
            assert spy.call_count == 1
            assert spy.call_args[0][0]["id"] == 2

    def test_staleness_check_triggers_rebuild_on_activity_count_change(self, tracker):
        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        first = tracker.get_tile_coverage_all()
        assert first.visited_count >= 1

        a2 = self._activity(2, [(41.0, -75.0), (41.001, -75.001)])
        tracker._activities_cache = [a1, a2]
        second = tracker.get_tile_coverage_all()
        assert second.visited_count > first.visited_count

    def test_bbox_filter_matches_full_rescan_baseline(self, tracker):
        """The bbox-filtered index result must match a from-scratch scan of
        the same activities using the exact tile-crossing math directly."""
        from src.coverage_tracker import _activity_tiles as activity_tiles_fn

        coords1 = [(40.7128, -74.0060), (40.72, -74.0), (40.73, -73.99)]
        coords2 = [(41.0, -75.0), (41.01, -75.0)]
        a1 = self._activity(1, coords1)
        a2 = self._activity(2, coords2)
        tracker._activities_cache = [a1, a2]

        bounds = (40.0, -75.5, 41.5, -73.0)
        result = tracker.get_tile_coverage(bounds, zoom=TILE_ZOOM)

        min_tx, min_ty = lat_lon_to_tile(bounds[2], bounds[1], TILE_ZOOM)
        max_tx, max_ty = lat_lon_to_tile(bounds[0], bounds[3], TILE_ZOOM)
        expected = set()
        for coords in (coords1, coords2):
            for tx, ty in activity_tiles_fn(coords, TILE_ZOOM):
                if min_tx <= tx <= max_tx and min_ty <= ty <= max_ty:
                    expected.add(f"{tx},{ty}")

        assert set(result.visited.keys()) == expected

    def test_concurrent_index_writes_produce_valid_json(self, tracker):
        """Two threads building the index at once for different zooms must
        not corrupt each other's cache file (atomic write via temp+replace)."""
        import threading as th

        activities = [self._activity(i, [(40.0 + i * 0.01, -74.0), (40.01 + i * 0.01, -74.01)])
                      for i in range(20)]
        tracker._activities_cache = activities

        errors = []

        def build(zoom):
            try:
                tracker._build_or_update_tile_index(zoom)
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        threads = [th.Thread(target=build, args=(TILE_ZOOM,)) for _ in range(4)]
        threads += [th.Thread(target=build, args=(SQUADRATINHO_ZOOM,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []
        for zoom in (TILE_ZOOM, SQUADRATINHO_ZOOM):
            path = tracker._tile_index_path(zoom)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)  # must not raise — valid JSON
            assert "tiles" in data


# ── per-zoom locking / copy-on-write (#558, absorbs #559) ────────

class TestPerZoomLocking:
    """A single global lock across every zoom meant a cold rebuild at one
    zoom (e.g. squadratinho) serialized reads/writes at an already-warm
    zoom (squadrat) behind it. #558 redesigns this as per-zoom locks plus
    copy-on-write index updates, which also fixes #559: a reader iterating
    index["tiles"] after _build_or_update_tile_index() returns (outside any
    lock) used to be exposed to a concurrent rebuild mutating that exact
    same dict object out from under it."""

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

    @staticmethod
    def _activity(act_id, coords, date="2026-01-01"):
        import polyline as codec
        return {"id": act_id, "polyline": codec.encode(coords), "start_date": date, "type": "Ride"}

    def test_different_zooms_use_different_lock_objects(self, tracker):
        lock_a = tracker._get_zoom_lock(TILE_ZOOM)
        lock_b = tracker._get_zoom_lock(SQUADRATINHO_ZOOM)
        assert lock_a is not lock_b

    def test_same_zoom_reuses_same_lock_object(self, tracker):
        assert tracker._get_zoom_lock(TILE_ZOOM) is tracker._get_zoom_lock(TILE_ZOOM)

    def test_cold_rebuild_at_one_zoom_does_not_block_another_zoom(self, tracker):
        """A slow build at SQUADRATINHO_ZOOM must not hold up a concurrent
        read/build at TILE_ZOOM (#558) — the old design shared one lock
        across every zoom."""
        import threading as th

        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]

        release_slow_zoom = th.Event()
        entered_slow_zoom = th.Event()
        real_decode = tracker._decode_activity_coords

        def slow_decode(activity):
            entered_slow_zoom.set()
            release_slow_zoom.wait(timeout=5)
            return real_decode(activity)

        with patch.object(tracker, "_decode_activity_coords", side_effect=slow_decode):
            t = th.Thread(target=tracker._build_or_update_tile_index, args=(SQUADRATINHO_ZOOM,))
            t.start()
            assert entered_slow_zoom.wait(timeout=5), "slow zoom build never started"

            # TILE_ZOOM must complete promptly even though SQUADRATINHO_ZOOM's
            # build is blocked mid-decode — this would hang under the old
            # single global lock.
            fast_result = tracker._build_or_update_tile_index(TILE_ZOOM)
            assert fast_result["tiles"]

            release_slow_zoom.set()
            t.join(timeout=5)
            assert not t.is_alive()

    def test_reader_iterating_old_snapshot_survives_concurrent_rebuild(self, tracker):
        """Regression for #559: a reader that already has a reference to
        index["tiles"] (as get_tile_coverage() does, after the lock is
        released) must not see a RuntimeError or a torn/partial dict if
        another thread rebuilds the same zoom's index concurrently —
        copy-on-write means the rebuild publishes a brand new dict rather
        than mutating the one the reader is iterating."""
        import threading as th

        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        index = tracker._build_or_update_tile_index(TILE_ZOOM)
        tiles_snapshot = index["tiles"]
        assert len(tiles_snapshot) >= 1
        snapshot_keys_before = set(tiles_snapshot.keys())

        a2 = self._activity(2, [(41.0, -75.0), (41.001, -75.001)])
        tracker._activities_cache = [a1, a2]

        errors = []

        def rebuild():
            try:
                tracker._build_or_update_tile_index(TILE_ZOOM)
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        t = th.Thread(target=rebuild)
        t.start()
        collected = []
        for key, entry in tiles_snapshot.items():  # iterating the OLD dict
            collected.append(key)
            time.sleep(0.001)  # widen the race window
        t.join(timeout=5)

        assert errors == []
        # The old snapshot must be exactly as it was — never mutated by the
        # concurrent rebuild, which published a separate new dict instead.
        assert set(collected) == snapshot_keys_before
        assert set(tiles_snapshot.keys()) == snapshot_keys_before

    def test_new_activity_touching_existing_tile_does_not_mutate_old_entry(self, tracker):
        """A new activity that crosses an already-indexed tile must produce
        a *new* entry object rather than appending to the old one in place
        — otherwise a reader holding the old published index would see the
        new activity_id show up in an entry it already has a reference to."""
        coords = [(40.7128, -74.0060)]
        a1 = self._activity(1, coords)
        tracker._activities_cache = [a1]
        first_index = tracker._build_or_update_tile_index(TILE_ZOOM)
        old_entry = next(iter(first_index["tiles"].values()))
        assert old_entry["activity_ids"] == [1]

        a2 = self._activity(2, coords)  # same tile, new activity
        tracker._activities_cache = [a1, a2]
        second_index = tracker._build_or_update_tile_index(TILE_ZOOM)
        new_entry = next(iter(second_index["tiles"].values()))

        assert new_entry["activity_ids"] == [1, 2]
        # The entry object held by the first snapshot is untouched.
        assert old_entry["activity_ids"] == [1]


# ── stale-serving on lock contention (#563) ───────────────────────

class TestStaleServingOnLockContention:
    """get_tile_coverage() must fail fast rather than block the requesting
    thread for a full rebuild's duration: if another thread already holds
    the zoom's lock (a rebuild in progress — cold start, #560 pre-warm, or
    a concurrent request), it should immediately return the last-published
    snapshot marked stale=True instead of waiting."""

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

    @staticmethod
    def _activity(act_id, coords, date="2026-01-01"):
        import polyline as codec
        return {"id": act_id, "polyline": codec.encode(coords), "start_date": date, "type": "Ride"}

    BOUNDS = (40.0, -75.5, 41.5, -73.0)

    def test_get_tile_coverage_not_stale_when_lock_is_free(self, tracker):
        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        result = tracker.get_tile_coverage(self.BOUNDS, zoom=TILE_ZOOM)
        assert result.stale is False
        assert "stale" in result.to_dict()
        assert result.to_dict()["stale"] is False

    def test_get_tile_coverage_serves_stale_snapshot_without_blocking(self, tracker):
        """While another thread holds TILE_ZOOM's lock mid-rebuild, a
        concurrent get_tile_coverage() call must return immediately with
        the previously-published snapshot and stale=True, not block until
        the slow rebuild finishes."""
        import threading as th

        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        # Publish an initial snapshot so there's something to serve as stale.
        first = tracker.get_tile_coverage(self.BOUNDS, zoom=TILE_ZOOM)
        assert first.stale is False
        assert first.visited_count >= 1

        a2 = self._activity(2, [(41.0, -75.0), (41.001, -75.001)])
        tracker._activities_cache = [a1, a2]

        entered_slow_build = th.Event()
        release_slow_build = th.Event()
        real_decode = tracker._decode_activity_coords

        def slow_decode(activity):
            entered_slow_build.set()
            release_slow_build.wait(timeout=5)
            return real_decode(activity)

        with patch.object(tracker, "_decode_activity_coords", side_effect=slow_decode):
            t = th.Thread(target=tracker._build_or_update_tile_index, args=(TILE_ZOOM,))
            t.start()
            assert entered_slow_build.wait(timeout=5), "slow rebuild never started"

            start = time.monotonic()
            stale_result = tracker.get_tile_coverage(self.BOUNDS, zoom=TILE_ZOOM)
            elapsed = time.monotonic() - start

            # Must return promptly — well under the time the slow rebuild
            # would take if this blocked on the same lock.
            assert elapsed < 1.0
            assert stale_result.stale is True
            # Stale snapshot is the pre-rebuild data (activity 2 not yet folded in).
            assert stale_result.visited_count == first.visited_count

            release_slow_build.set()
            t.join(timeout=5)
            assert not t.is_alive()

        # Next call, after the rebuild finished, sees fresh (non-stale) data.
        fresh_result = tracker.get_tile_coverage(self.BOUNDS, zoom=TILE_ZOOM)
        assert fresh_result.stale is False
        assert fresh_result.visited_count > first.visited_count

    def test_falls_back_to_blocking_when_no_snapshot_published_yet(self, tracker):
        """A genuinely cold zoom (nothing published in memory yet) has no
        stale snapshot to serve, so this must still block and return a
        real (non-stale) result rather than an empty one."""
        import threading as th

        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]

        entered_slow_build = th.Event()
        release_slow_build = th.Event()
        real_decode = tracker._decode_activity_coords

        def slow_decode(activity):
            entered_slow_build.set()
            release_slow_build.wait(timeout=5)
            return real_decode(activity)

        with patch.object(tracker, "_decode_activity_coords", side_effect=slow_decode):
            t = th.Thread(target=tracker._build_or_update_tile_index, args=(TILE_ZOOM,))
            t.start()
            assert entered_slow_build.wait(timeout=5), "slow rebuild never started"

            # No snapshot exists yet in tracker._tile_index_cache — must block
            # rather than return nothing.
            release_thread = th.Thread(target=lambda: (time.sleep(0.1), release_slow_build.set()))
            release_thread.start()
            result = tracker.get_tile_coverage(self.BOUNDS, zoom=TILE_ZOOM)
            release_thread.join()

            assert result.stale is False
            assert result.visited_count >= 1

            t.join(timeout=5)
            assert not t.is_alive()

    def test_get_tile_index_or_stale_direct(self, tracker):
        """Direct unit test of _get_tile_index_or_stale()'s (index, stale)
        contract, independent of get_tile_coverage()'s bbox filtering."""
        import threading as th

        a1 = self._activity(1, [(40.7128, -74.0060), (40.7130, -74.0058)])
        tracker._activities_cache = [a1]
        index, stale = tracker._get_tile_index_or_stale(TILE_ZOOM)
        assert stale is False
        assert index["tiles"]

        lock = tracker._get_zoom_lock(TILE_ZOOM)
        lock.acquire()
        try:
            index2, stale2 = tracker._get_tile_index_or_stale(TILE_ZOOM)
            assert stale2 is True
            assert index2 is index  # exact same published snapshot object
        finally:
            lock.release()


# ── roadless (open-water) tile detection (#525) ──────────────────

class TestGetRoadlessTiles:
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

    # Small bbox that spans exactly a 2x2 tile block at TILE_ZOOM.
    _x0, _y0 = lat_lon_to_tile(40.7, -74.0, TILE_ZOOM)
    _south, _west, _, _ = tile_to_bounds(_x0, _y0 + 1, TILE_ZOOM)
    _, _, _north, _east = tile_to_bounds(_x0 + 1, _y0, TILE_ZOOM)
    BOUNDS = (_south, _west, _north, _east)

    @staticmethod
    def _overpass_response(elements):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"elements": elements}
        return resp

    def test_no_water_marks_every_tile_reachable(self, tracker):
        with patch("requests.post", return_value=self._overpass_response([])):
            result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)

        assert result["status"] == "success"
        assert result["roadless"] == []

    def test_water_polygon_covering_bounds_marks_every_tile_roadless(self, tracker):
        # A single "natural=water" way whose ring encloses the whole bbox —
        # every tile's center falls inside it.
        south, west, north, east = self.BOUNDS
        pad = 1.0  # degrees — comfortably outside the small test bbox
        ring = [
            {"lat": south - pad, "lon": west - pad},
            {"lat": south - pad, "lon": east + pad},
            {"lat": north + pad, "lon": east + pad},
            {"lat": north + pad, "lon": west - pad},
            {"lat": south - pad, "lon": west - pad},
        ]
        elements = [{"type": "way", "geometry": ring}]

        with patch("requests.post", return_value=self._overpass_response(elements)):
            result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)

        assert result["status"] == "success"
        min_tx, min_ty = lat_lon_to_tile(north, west, TILE_ZOOM)
        max_tx, max_ty = lat_lon_to_tile(south, east, TILE_ZOOM)
        expected_count = (max_tx - min_tx + 1) * (max_ty - min_ty + 1)
        assert len(result["roadless"]) == expected_count

    def test_water_relation_outer_ring_is_used(self, tracker):
        south, west, north, east = self.BOUNDS
        pad = 1.0
        ring = [
            {"lat": south - pad, "lon": west - pad},
            {"lat": south - pad, "lon": east + pad},
            {"lat": north + pad, "lon": east + pad},
            {"lat": north + pad, "lon": west - pad},
            {"lat": south - pad, "lon": west - pad},
        ]
        elements = [{
            "type": "relation",
            "members": [{"role": "outer", "geometry": ring}],
        }]

        with patch("requests.post", return_value=self._overpass_response(elements)):
            result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)

        assert result["status"] == "success"
        assert len(result["roadless"]) > 0

    def test_water_far_from_bounds_leaves_tiles_reachable(self, tracker):
        # A water polygon nowhere near the query bbox shouldn't mark any
        # tile as roadless.
        ring = [
            {"lat": 10.0, "lon": 10.0},
            {"lat": 10.0, "lon": 10.1},
            {"lat": 10.1, "lon": 10.1},
            {"lat": 10.1, "lon": 10.0},
            {"lat": 10.0, "lon": 10.0},
        ]
        elements = [{"type": "way", "geometry": ring}]

        with patch("requests.post", return_value=self._overpass_response(elements)):
            result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)

        assert result["status"] == "success"
        assert result["roadless"] == []

    def test_result_uses_cached_polygons_on_second_call(self, tracker):
        with patch("requests.post", return_value=self._overpass_response([])) as mock_post:
            tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)
            tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)

        mock_post.assert_called_once()

    def test_overpass_failure_returns_error_status(self, tracker):
        with patch("requests.post", side_effect=OSError("network down")):
            result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)
        assert result["status"] == "error"

    def test_nearby_viewport_reuses_cached_water_polygons(self, tracker):
        # Two distinct-but-nearby bboxes, as explore.js would send for a
        # small pan/zoom — both fall in the same grid cell, so this should
        # be one Overpass call, not two (the bug this guards against: keying
        # the cache on the exact viewport bbox made it an almost-always-miss,
        # so every pan/zoom paid out a fresh Overpass round-trip).
        south, west, north, east = self.BOUNDS
        nudged = (south + 0.001, west + 0.001, north + 0.001, east + 0.001)
        assert nudged != self.BOUNDS

        with patch("requests.post", return_value=self._overpass_response([])) as mock_post:
            tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)
            tracker.get_roadless_tiles(nudged, zoom=TILE_ZOOM)

        mock_post.assert_called_once()

    def test_concurrent_requests_for_same_bbox_share_one_overpass_call(self, tracker):
        """explore.js "both" mode fires zoom=14 and zoom=17 roadless-tile
        requests for the identical viewport bounds, from separate threads
        (gthread workers) at effectively the same time. Without a per-key
        lock, both would independently miss the cache and each fire their
        own Overpass query; this asserts they instead share one."""
        call_count = 0
        both_started = threading.Barrier(2, timeout=5)

        def slow_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Give the second thread a chance to reach the lock while the
            # first is "mid-request" — proves the second waits for the
            # first's result rather than firing its own concurrent query.
            time.sleep(0.05)
            return self._overpass_response([])

        results = {}

        def worker(name, zoom):
            try:
                both_started.wait()
            except threading.BrokenBarrierError:
                pass
            results[name] = tracker.get_roadless_tiles(self.BOUNDS, zoom=zoom)

        with patch("requests.post", side_effect=slow_post):
            t14 = threading.Thread(target=worker, args=("zoom14", TILE_ZOOM))
            t17 = threading.Thread(target=worker, args=("zoom17", SQUADRATINHO_ZOOM))
            t14.start()
            t17.start()
            t14.join(timeout=5)
            t17.join(timeout=5)

        assert call_count == 1
        assert results["zoom14"]["status"] == "success"
        assert results["zoom17"]["status"] == "success"


# ── get_roadless_tiles() bbox prefilter (#574) ─────────────────────

class TestRoadlessTilesBboxPrefilter:
    """get_roadless_tiles()/_point_in_polygon() previously ran a full
    ray-cast for every tile against every water polygon with no cheap
    reject first. #574 precomputes each polygon's bbox once per call and
    skips the ray-cast entirely for a tile whose center falls outside it —
    not a per-(bbox,zoom) result cache (deliberately not added; see
    get_tile_coverage()'s own docstring on why that pattern was dropped)."""

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

    # A wider bbox spanning a 6x6 tile block at TILE_ZOOM, so a small
    # water polygon tucked in one corner leaves plenty of tiles whose
    # centers fall outside its bbox.
    _x0, _y0 = lat_lon_to_tile(40.7, -74.0, TILE_ZOOM)
    _south, _west, _, _ = tile_to_bounds(_x0, _y0 + 5, TILE_ZOOM)
    _, _, _north, _east = tile_to_bounds(_x0 + 5, _y0, TILE_ZOOM)
    BOUNDS = (_south, _west, _north, _east)

    @staticmethod
    def _overpass_response(elements):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"elements": elements}
        return resp

    def test_polygon_bbox_computes_correct_extent(self, tracker):
        polygon = [(10.0, 20.0), (10.0, 25.0), (15.0, 25.0), (15.0, 20.0), (10.0, 20.0)]
        assert tracker._polygon_bbox(polygon) == (10.0, 20.0, 15.0, 25.0)

    def test_prefilter_skips_ray_cast_for_tiles_outside_polygon_bbox(self, tracker):
        """A small water polygon confined to one corner of the bbox must
        not trigger a _point_in_polygon call for tiles whose centers fall
        outside that polygon's own bbox."""
        # A tiny polygon around the single tile at (x0, y0) only.
        t_south, t_west, t_north, t_east = tile_to_bounds(self._x0, self._y0, TILE_ZOOM)
        ring = [
            {"lat": t_south, "lon": t_west},
            {"lat": t_south, "lon": t_east},
            {"lat": t_north, "lon": t_east},
            {"lat": t_north, "lon": t_west},
            {"lat": t_south, "lon": t_west},
        ]
        elements = [{"type": "way", "geometry": ring}]

        with patch("requests.post", return_value=self._overpass_response(elements)):
            with patch.object(
                tracker, "_point_in_polygon", wraps=tracker._point_in_polygon
            ) as spy:
                result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)

        assert result["status"] == "success"
        min_tx, min_ty = lat_lon_to_tile(self._north, self._west, TILE_ZOOM)
        max_tx, max_ty = lat_lon_to_tile(self._south, self._east, TILE_ZOOM)
        total_tiles = (max_tx - min_tx + 1) * (max_ty - min_ty + 1)
        assert total_tiles > 4  # sanity: bbox is meaningfully larger than the polygon

        # The prefilter must reject the vast majority of tiles before ever
        # calling the full ray-cast test.
        assert spy.call_count < total_tiles

    def test_prefilter_result_matches_brute_force_ray_cast(self, tracker):
        """Correctness guard: the bbox-prefiltered result must be identical
        to what a full ray-cast-every-tile sweep would produce — the
        prefilter is a same-call speedup, not a behavior change."""
        # An irregular polygon covering roughly the left half of the bbox.
        mid_lon = (self._west + self._east) / 2
        pad = 0.001
        ring = [
            {"lat": self._south - pad, "lon": self._west - pad},
            {"lat": self._south - pad, "lon": mid_lon},
            {"lat": self._north + pad, "lon": mid_lon},
            {"lat": self._north + pad, "lon": self._west - pad},
            {"lat": self._south - pad, "lon": self._west - pad},
        ]
        elements = [{"type": "way", "geometry": ring}]

        with patch("requests.post", return_value=self._overpass_response(elements)):
            result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)
        assert result["status"] == "success"
        prefiltered = {(t["x"], t["y"]) for t in result["roadless"]}

        # Brute-force: ray-cast every tile center against the raw polygon,
        # no bbox shortcut at all.
        polygon = [(pt["lat"], pt["lon"]) for pt in ring]
        min_tx, min_ty = lat_lon_to_tile(self._north, self._west, TILE_ZOOM)
        max_tx, max_ty = lat_lon_to_tile(self._south, self._east, TILE_ZOOM)
        brute_force = set()
        for tx in range(min_tx, max_tx + 1):
            for ty in range(min_ty, max_ty + 1):
                t_south, t_west, t_north, t_east = tile_to_bounds(tx, ty, TILE_ZOOM)
                center_lat = (t_south + t_north) / 2
                center_lon = (t_west + t_east) / 2
                if tracker._point_in_polygon(center_lat, center_lon, polygon):
                    brute_force.add((tx, ty))

        assert prefiltered == brute_force
        assert len(brute_force) > 0  # sanity: the polygon actually covers some tiles

    def test_no_polygons_means_no_ray_cast_calls_at_all(self, tracker):
        with patch("requests.post", return_value=self._overpass_response([])):
            with patch.object(
                tracker, "_point_in_polygon", wraps=tracker._point_in_polygon
            ) as spy:
                result = tracker.get_roadless_tiles(self.BOUNDS, zoom=TILE_ZOOM)

        assert result["roadless"] == []
        spy.assert_not_called()


# ── bbox cache key (#481, used for water-polygon caching) ────────

class TestBboxCacheKey:
    def test_different_bounds_give_different_keys(self):
        k1 = _bbox_cache_key((40.0, -75.0, 41.0, -74.0))
        k2 = _bbox_cache_key((10.0, 10.0, 11.0, 11.0))
        assert k1 != k2

    def test_same_bounds_give_same_key(self):
        k1 = _bbox_cache_key((40.0, -75.0, 41.0, -74.0))
        k2 = _bbox_cache_key((40.0, -75.0, 41.0, -74.0))
        assert k1 == k2

    def test_rounding_collapses_near_identical_bounds(self):
        k1 = _bbox_cache_key((40.000001, -75.0, 41.0, -74.0))
        k2 = _bbox_cache_key((40.000002, -75.0, 41.0, -74.0))
        assert k1 == k2


# ── water-polygon cache grid snapping ─────────────────────────────

class TestSnapBboxToGrid:
    def test_already_aligned_bbox_is_unchanged(self):
        bounds = (40.0, -75.0, 41.0, -74.0)
        assert _snap_bbox_to_grid(bounds, 0.5) == bounds

    def test_unaligned_bbox_expands_outward(self):
        bounds = (40.1, -74.9, 40.4, -74.6)
        snapped = _snap_bbox_to_grid(bounds, 0.5)
        south, west, north, east = snapped
        # Contains the original bbox...
        assert south <= bounds[0] and west <= bounds[1]
        assert north >= bounds[2] and east >= bounds[3]
        # ...and lands exactly on the grid.
        for v in snapped:
            assert math.isclose(v / 0.5, round(v / 0.5), abs_tol=1e-9)

    def test_nearby_bboxes_snap_to_same_cell(self):
        a = _snap_bbox_to_grid((40.10, -74.90, 40.40, -74.60), _WATER_POLYGON_GRID_DEGREES)
        b = _snap_bbox_to_grid((40.15, -74.95, 40.45, -74.65), _WATER_POLYGON_GRID_DEGREES)
        assert a == b


# ── legacy coverage_tiles_*.json cleanup (#555) ────────────────────

class TestLegacyCoverageTileSweep:
    """The pre-tile-index-rewrite per-bbox cache (coverage_tiles_*.json) is
    dead weight nothing writes anymore, but was previously only cleaned up
    inside invalidate_caches() — which, on the production Pi, apparently
    hadn't run since the rewrite: 38 files / 32MB were still sitting there
    over five weeks later. _sweep_legacy_coverage_tile_files() now also runs
    unconditionally at __init__ so a deployment self-heals on its next
    restart rather than waiting on a resync that may never come."""

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

    def test_sweep_removes_legacy_files(self, tracker):
        for i in range(3):
            (tracker.cache_dir / f"coverage_tiles_17_fake{i}.json").write_text("{}")
        (tracker.cache_dir / "coverage_tiles_14_all.json").write_text("{}")

        removed = tracker._sweep_legacy_coverage_tile_files()

        assert removed == 4
        assert list(tracker.cache_dir.glob("coverage_tiles_*.json")) == []

    def test_sweep_leaves_current_caches_untouched(self, tracker):
        (tracker.cache_dir / "coverage_tiles_17_fake.json").write_text("{}")
        (tracker.cache_dir / "tile_index_14.json").write_text("{}")
        (tracker.cache_dir / "water_abc123.json").write_text("{}")

        tracker._sweep_legacy_coverage_tile_files()

        remaining = {p.name for p in tracker.cache_dir.glob("*.json")}
        assert remaining == {"tile_index_14.json", "water_abc123.json"}

    def test_sweep_is_a_no_op_when_nothing_legacy_exists(self, tracker):
        assert tracker._sweep_legacy_coverage_tile_files() == 0

    def test_init_calls_the_sweep(self, mock_config):
        """Verifies the __init__ wiring without touching the real filesystem
        default (data/cache) — the sweep itself is exercised directly above."""
        with patch.object(CoverageTracker, '_sweep_legacy_coverage_tile_files', return_value=0) as mock_sweep:
            CoverageTracker(mock_config)
        mock_sweep.assert_called_once()

    def test_hard_invalidate_caches_still_removes_legacy_files(self, tracker):
        """Regression guard: hard_invalidate_caches() used to inline this
        glob/unlink loop directly; it now delegates to
        _sweep_legacy_coverage_tile_files()."""
        (tracker.cache_dir / "coverage_tiles_17_fake.json").write_text("{}")
        tracker.hard_invalidate_caches()
        assert list(tracker.cache_dir.glob("coverage_tiles_*.json")) == []


# ── water_polygon cache TTL (#532) ─────────────────────────────────

class TestCacheTtl:
    """The water-polygon file cache never expired on its own (only
    count-based eviction / explicit invalidate_caches()). An optional TTL
    lets a cached file be treated as stale by age alone."""

    BOUNDS = (40.0, -75.0, 41.0, -74.0)

    @pytest.fixture
    def tracker(self, tmp_path):
        config = MagicMock()
        self._config_values = {}
        config.get = MagicMock(side_effect=lambda key, default=None: self._config_values.get(key, default))
        t = CoverageTracker(config)
        t.cache_dir = tmp_path
        return t

    def _age_file(self, path: Path, age_seconds: float) -> None:
        now = time.time()
        os.utime(path, (now - age_seconds, now - age_seconds))

    def test_water_polygons_reused_when_default_ttl_disabled(self, tracker):
        cache_file = tracker.cache_dir / f"water_{_bbox_cache_key(self.BOUNDS)}.json"
        cache_file.write_text(json.dumps([[[40.1, -74.5], [40.2, -74.5], [40.2, -74.4]]]))
        self._age_file(cache_file, age_seconds=10_000_000)

        with patch("requests.post") as mock_post:
            polygons = tracker._get_or_fetch_water_polygons(self.BOUNDS)

        assert len(polygons) == 1
        mock_post.assert_not_called()

    def test_water_polygons_refetched_once_stale(self, tracker):
        self._config_values["exploration.water_polygon_cache_ttl_seconds"] = 3600
        cache_file = tracker.cache_dir / f"water_{_bbox_cache_key(self.BOUNDS)}.json"
        cache_file.write_text(json.dumps([[[40.1, -74.5], [40.2, -74.5], [40.2, -74.4]]]))
        self._age_file(cache_file, age_seconds=7200)

        mock_response = MagicMock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_response) as mock_post:
            polygons = tracker._get_or_fetch_water_polygons(self.BOUNDS)

        assert polygons == []
        mock_post.assert_called_once()


# ── Overpass timeout / retry / negative cache (#562) ──────────────

class TestOverpassTimeoutAndNegativeCache:
    """_get_or_fetch_water_polygons() previously made a single
    requests.post(timeout=30) call with a [timeout:25] Overpass query and
    no negative cache, so a slow/degraded Overpass endpoint made every
    roadless-tile request pay out a ~30s wait, one at a time, forever."""

    BOUNDS = (40.0, -75.0, 41.0, -74.0)

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

    @staticmethod
    def _overpass_response(elements=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"elements": elements or []}
        return resp

    def test_client_and_query_timeouts_are_lowered_together(self, tracker):
        """Both the client-side requests.post timeout and Overpass's own
        internal [out:json][timeout:N] budget must be lowered together
        (~10-12s) — lowering only the client side would abort queries
        Overpass would've legitimately finished."""
        from src.coverage_tracker import _OVERPASS_QUERY_TIMEOUT_S, _OVERPASS_REQUEST_TIMEOUT_S

        assert _OVERPASS_REQUEST_TIMEOUT_S <= 12
        assert _OVERPASS_QUERY_TIMEOUT_S <= 12
        # Client timeout must not be tighter than Overpass's own query
        # budget, or we'd abort queries Overpass was about to finish.
        assert _OVERPASS_REQUEST_TIMEOUT_S >= _OVERPASS_QUERY_TIMEOUT_S

        with patch("requests.post", return_value=self._overpass_response()) as mock_post:
            tracker._get_or_fetch_water_polygons(self.BOUNDS)

        _, kwargs = mock_post.call_args
        assert kwargs["timeout"] == _OVERPASS_REQUEST_TIMEOUT_S
        sent_query = mock_post.call_args[1]["data"]["data"]
        assert f"[timeout:{_OVERPASS_QUERY_TIMEOUT_S}]" in sent_query

    def test_failure_sets_negative_cache_and_fails_fast_on_next_call(self, tracker):
        """A failed Overpass call must mark the endpoint so the very next
        call (different bbox — an outage is endpoint-wide) fails
        immediately instead of paying out another full timeout."""
        with patch("requests.post", side_effect=requests.ConnectionError("boom")) as mock_post:
            with pytest.raises(Exception):
                tracker._get_or_fetch_water_polygons(self.BOUNDS)

        other_bounds = (10.0, 10.0, 11.0, 11.0)
        with patch("requests.post", return_value=self._overpass_response()) as mock_post2:
            with pytest.raises(Exception):
                tracker._get_or_fetch_water_polygons(other_bounds)
            # Negative cache means the second bbox's request never even
            # tried the network.
            mock_post2.assert_not_called()

    def test_negative_cache_key_is_endpoint_not_bbox(self, tracker):
        """Regression guard: the marker must be keyed by endpoint URL, not
        by bbox — a bbox-keyed marker would miss on nearly every call since
        the bbox changes on every pin placement."""
        from src.coverage_tracker import _OVERPASS_URL

        with patch("requests.post", side_effect=requests.ConnectionError("boom")):
            with pytest.raises(Exception):
                tracker._get_or_fetch_water_polygons(self.BOUNDS)

        assert _OVERPASS_URL in tracker._overpass_failure_until
        assert self.BOUNDS not in tracker._overpass_failure_until

    def test_negative_cache_expires_after_ttl(self, tracker):
        """Once the negative-cache window has passed, the next call must
        hit the network again rather than staying blocked forever."""
        from src.coverage_tracker import _OVERPASS_URL

        # Simulate a failure marker that already expired.
        tracker._overpass_failure_until[_OVERPASS_URL] = time.time() - 1

        with patch("requests.post", return_value=self._overpass_response()) as mock_post:
            polygons = tracker._get_or_fetch_water_polygons(self.BOUNDS)

        assert polygons == []
        mock_post.assert_called_once()

    def test_success_clears_a_stale_negative_cache_marker(self, tracker):
        from src.coverage_tracker import _OVERPASS_URL

        with patch("requests.post", side_effect=requests.ConnectionError("boom")):
            with pytest.raises(Exception):
                tracker._get_or_fetch_water_polygons(self.BOUNDS)
        assert _OVERPASS_URL in tracker._overpass_failure_until

        # Manually expire the marker (simulating TTL elapsed) and retry —
        # a subsequent success should clear it so it doesn't linger.
        tracker._overpass_failure_until[_OVERPASS_URL] = time.time() - 1
        other_bounds = (10.0, 10.0, 11.0, 11.0)
        with patch("requests.post", return_value=self._overpass_response()):
            tracker._get_or_fetch_water_polygons(other_bounds)

        assert _OVERPASS_URL not in tracker._overpass_failure_until

    def test_water_polygon_cache_write_leaves_no_tmp_file_behind(self, tracker):
        with patch("requests.post", return_value=self._overpass_response()):
            tracker._get_or_fetch_water_polygons(self.BOUNDS)

        cache_file = tracker.cache_dir / f"water_{_bbox_cache_key(self.BOUNDS)}.json"
        assert cache_file.exists()
        with open(cache_file, "r", encoding="utf-8") as f:
            json.load(f)  # must be valid, complete JSON
        tmp_files = list(tracker.cache_dir.glob("water_*.tmp*"))
        assert tmp_files == []
