"""Drawn-area fence for Explore road routes: when the rider draws a box, the
ORS route is fenced inside it with thin avoid_polygons strips just outside
each edge. Phase 2 used to ignore the box entirely (its padding detours ran
straight out of it)."""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.exploration_service import ExplorationService

_RAW = {
    "features": [{
        "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
        "properties": {
            "summary": {"distance": 1000.0, "duration": 300.0},
            "extras": {},
        },
    }],
}
_WPS = [[41.98, -87.65], [41.99, -87.64]]
_BOX = [41.95, -87.80, 42.10, -87.60]


@pytest.fixture
def service_with_key(tmp_path):
    config = MagicMock()
    config.get = MagicMock(side_effect=lambda key, default=None: 'fake-key' if key == 'ors.api_key' else default)
    with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=config):
        svc = ExplorationService()
    svc._tracker.cache_dir = tmp_path
    return svc


@pytest.mark.unit
class TestFencePolygons:
    def test_strips_sit_outside_every_edge(self):
        south, west, north, east = _BOX
        fence = ExplorationService._fence_polygons(tuple(_BOX))
        assert fence["type"] == "MultiPolygon"
        assert len(fence["coordinates"]) >= 4
        for poly in fence["coordinates"]:
            ring = poly[0]
            assert ring[0] == ring[-1]
            lons = [p[0] for p in ring]
            lats = [p[1] for p in ring]
            # Entirely beyond at least one edge — never overlapping the box.
            assert (min(lats) > north or max(lats) < south
                    or min(lons) > east or max(lons) < west)

    def test_strips_are_segmented_under_ors_extent_limit(self):
        fence = ExplorationService._fence_polygons((41.5, -88.3, 42.4, -87.5))   # ~100 x 66 km
        for poly in fence["coordinates"]:
            ring = poly[0]
            lat_span_m = (max(p[1] for p in ring) - min(p[1] for p in ring)) * 111320
            lon_span_m = (max(p[0] for p in ring) - min(p[0] for p in ring)) * 111320 * 0.74
            assert max(lat_span_m, lon_span_m) < 20000

    def test_corners_are_closed(self):
        """North/south strips extend past the west/east strips' outer edges."""
        south, west, north, east = _BOX
        fence = ExplorationService._fence_polygons(tuple(_BOX))
        north_strip_lons = [p[0] for poly in fence["coordinates"] for p in poly[0]
                            if min(q[1] for q in poly[0]) > north]
        west_strip_lons = [p[0] for poly in fence["coordinates"] for p in poly[0]
                           if max(q[0] for q in poly[0]) < west]
        assert min(north_strip_lons) <= min(west_strip_lons)


@pytest.mark.unit
class TestComputeRouteWithBounds:
    def test_bounds_passes_avoid_polygons_and_flags_enforced(self, service_with_key):
        with patch("src.ors_client.get_route", return_value=_RAW) as mock_get:
            result = service_with_key.compute_route(_WPS, bounds=_BOX)
        assert mock_get.call_args.kwargs["avoid_polygons"]["type"] == "MultiPolygon"
        assert result["status"] == "success"
        assert result["bounds_enforced"] is True

    def test_no_bounds_sends_no_avoid_polygons(self, service_with_key):
        with patch("src.ors_client.get_route", return_value=_RAW) as mock_get:
            result = service_with_key.compute_route(_WPS)
        assert "avoid_polygons" not in mock_get.call_args.kwargs
        assert "bounds_enforced" not in result

    def test_fenced_and_unfenced_cached_separately(self, service_with_key):
        with patch("src.ors_client.get_route", return_value=_RAW) as mock_get:
            service_with_key.compute_route(_WPS)
            service_with_key.compute_route(_WPS, bounds=_BOX)
            service_with_key.compute_route(_WPS, bounds=_BOX)
        assert mock_get.call_count == 2

    def test_fenced_failure_falls_back_unfenced(self, service_with_key):
        """If ORS rejects the fenced request, route unfenced and say so."""
        def fake(coords, profile, **kwargs):
            return None if "avoid_polygons" in kwargs else _RAW
        with patch("src.ors_client.get_route", side_effect=fake) as mock_get:
            result = service_with_key.compute_route(_WPS, bounds=_BOX)
        assert mock_get.call_count == 2
        assert result["status"] == "success"
        assert result["bounds_enforced"] is False

    def test_rate_limit_does_not_trigger_unfenced_retry(self, service_with_key):
        with patch("src.ors_client.get_route", return_value={"_ors_rate_limited": True}) as mock_get:
            result = service_with_key.compute_route(_WPS, bounds=_BOX)
        assert mock_get.call_count == 1
        assert result["status"] == "error"
        assert "_rate_limited" not in result

    def test_fence_survives_cache_persist_roundtrip(self, service_with_key, tmp_path):
        with patch("src.ors_client.get_route", return_value=_RAW):
            service_with_key.compute_route(_WPS, bounds=_BOX)
        # compute_route schedules a background persist (#573) — let it land
        # rather than racing it with a second writer on the same tmp file.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            thread = service_with_key._persist_thread
            if thread is None or not thread.is_alive():
                break
            time.sleep(0.02)
        service_with_key._route_cache.clear()
        service_with_key._load_route_cache_from_disk()
        (key,) = service_with_key._route_cache.keys()
        assert key[3] == tuple(round(v, 5) for v in _BOX)


@pytest.mark.unit
class TestChunkedRoute:
    """ORS caps a request at 50 waypoints; longer lists (Explore's cluster
    sweep) are routed in chunks sharing boundary waypoints and stitched."""

    @staticmethod
    def _fake(coords, profile, **kwargs):
        # One straight segment per waypoint pair; 1 km each.
        n = len(coords)
        return {"features": [{
            "geometry": {"coordinates": coords},
            "properties": {"summary": {"distance": 1000.0 * (n - 1), "duration": 60.0 * (n - 1)}, "extras": {}},
        }]}

    def test_long_list_is_chunked_and_stitched(self, service_with_key):
        wps = [[41.9 + i * 0.001, -87.7] for i in range(120)]
        with patch("src.ors_client.get_route", side_effect=self._fake) as mock_get:
            result = service_with_key.compute_route(wps)
        assert result["status"] == "success"
        assert mock_get.call_count == 3                      # 50 + 50 + 22 (shared boundaries)
        for call in mock_get.call_args_list:
            assert len(call.args[0]) <= 50
        assert len(result["coordinates"]) == 120             # boundaries not duplicated
        assert result["coordinates"][0] == [41.9, -87.7]
        assert result["distance_km"] == pytest.approx(119.0)
        assert result["segments"] == 3

    def test_chunk_failure_fails_whole_route_with_segment(self, service_with_key):
        calls = {"n": 0}

        def flaky(coords, profile, **kwargs):
            calls["n"] += 1
            return None if calls["n"] == 2 else self._fake(coords, profile)
        wps = [[41.9 + i * 0.001, -87.7] for i in range(120)]
        with patch("src.ors_client.get_route", side_effect=flaky):
            result = service_with_key.compute_route(wps)
        assert result["status"] == "error"
        assert "segment 2 of 3" in result["message"]

    def test_short_list_is_not_chunked(self, service_with_key):
        with patch("src.ors_client.get_route", side_effect=self._fake) as mock_get:
            result = service_with_key.compute_route([[41.9 + i * 0.001, -87.7] for i in range(50)])
        assert mock_get.call_count == 1
        assert "segments" not in result


@pytest.mark.unit
class TestValidateRouteBounds:
    def test_valid_box(self):
        from app.api.planner_bp import _validate_route_bounds
        assert _validate_route_bounds([41.95, -87.80, 42.10, -87.60]) is None

    @pytest.mark.parametrize("bad", [
        [1, 2, 3],
        "41,-87,42,-86",
        [42.1, -87.8, 41.9, -87.6],          # south > north
        [41.9, -87.6, 42.1, -87.8],          # west > east
        [41.0, -88.0, 43.0, -87.0],          # too big
        [41.9, -87.8, float("nan"), -87.6],
        [True, -87.8, 42.1, -87.6],
    ])
    def test_rejects_bad_boxes(self, bad):
        from app.api.planner_bp import _validate_route_bounds
        assert _validate_route_bounds(bad) is not None
