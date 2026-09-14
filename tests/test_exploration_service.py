"""Tests for app/services/exploration_service.py and src/ors_client.py."""

import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.exploration_service import ExplorationService, _SURFACE_TO_PROFILE, MAX_ROUTE_CACHE_ENTRIES
from src.coverage_tracker import (
    TileCoverage,
    TILE_ZOOM,
    SQUADRATINHO_ZOOM,
    lat_lon_to_tile,
    tile_to_bounds,
)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get = MagicMock(side_effect=lambda key, default=None: default)
    return config


@pytest.fixture
def service(mock_config, tmp_path):
    with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=mock_config):
        svc = ExplorationService()
    # Isolate from the real data/cache/ dir — CoverageTracker's on-disk tile
    # cache has no expiration, so a real coverage_tiles_*_all.json left over
    # from actual app usage would otherwise be returned instead of the
    # empty/mocked _activities_cache the tests set up, making results depend
    # on whatever happens to be cached on the machine running the tests.
    svc._tracker.cache_dir = tmp_path
    return svc


def _wait_for_persist(svc, timeout=5):
    """Block until svc's background route-cache persist thread (#573) has
    finished its current run(s), so a test can assert on-disk state right
    after a compute_route() call that scheduled (but didn't synchronously
    perform) a write."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        thread = svc._persist_thread
        if thread is None or not thread.is_alive():
            return
        time.sleep(0.02)
    raise AssertionError("route-cache persist did not finish in time")


@pytest.fixture
def service_with_key(mock_config, tmp_path):
    """Service pre-configured with a fake ORS API key."""
    def _get(key, default=None):
        if key == 'ors.api_key':
            return 'fake-key'
        return default

    mock_config.get = MagicMock(side_effect=_get)
    with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=mock_config):
        svc = ExplorationService()
    svc._tracker.cache_dir = tmp_path
    return svc


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

    def test_hard_invalidate_caches(self, service):
        with patch.object(service._tracker, "hard_invalidate_caches") as mock_inv:
            service.hard_invalidate_caches()
            mock_inv.assert_called_once()


# ── cold-start pre-warm (#560) ────────────────────────────────────


class TestStartPrewarm:
    def test_prewarm_builds_both_zooms_sequentially(self, service):
        service._tracker._activities_cache = []
        calls = []
        build_lock = threading.Lock()

        def fake_build(zoom):
            with build_lock:
                calls.append(zoom)
            return {"indexed_activity_ids": set(), "tiles": {}}

        with patch.object(service._tracker, "_build_or_update_tile_index", side_effect=fake_build) as mock_build:
            service.start_prewarm()
            # Wait for the daemon thread to finish.
            for _ in range(50):
                if mock_build.call_count >= 2:
                    break
                time.sleep(0.05)

        assert calls == [TILE_ZOOM, SQUADRATINHO_ZOOM]

    def test_prewarm_is_single_fire(self, service):
        service._tracker._activities_cache = []
        with patch.object(
            service._tracker, "_build_or_update_tile_index",
            return_value={"indexed_activity_ids": set(), "tiles": {}},
        ) as mock_build:
            service.start_prewarm()
            service.start_prewarm()
            service.start_prewarm()
            for _ in range(50):
                if mock_build.call_count >= 2:
                    break
                time.sleep(0.05)

        # Exactly one pass over both zooms, despite three calls.
        assert mock_build.call_count == 2

    def test_prewarm_tolerates_missing_activities_file(self, service, tmp_path):
        # No activities.json written under tmp_path — _load_activities()
        # must treat this as "no activities yet", not raise.
        service._tracker._activities_cache = None
        service._tracker.cache_dir = tmp_path

        done = threading.Event()
        real_worker = service._prewarm_worker

        def wrapped_worker():
            real_worker()
            done.set()

        with patch.object(service, "_prewarm_worker", side_effect=wrapped_worker):
            service.start_prewarm()
            assert done.wait(timeout=5)

        # Both zooms built to an empty (but valid) index.
        for zoom in (TILE_ZOOM, SQUADRATINHO_ZOOM):
            path = service._tracker._tile_index_path(zoom)
            assert path.exists() or service._tracker._tile_index_cache.get(zoom) is not None

    def test_prewarm_survives_a_build_exception(self, service):
        """A failure building one zoom's index must be caught and logged,
        not crash the daemon thread or propagate to the caller — and the
        other zoom should still get a chance to warm."""
        service._tracker._activities_cache = []
        calls = []

        def flaky_build(zoom):
            calls.append(zoom)
            if zoom == TILE_ZOOM:
                raise RuntimeError("simulated failure")
            return {"indexed_activity_ids": set(), "tiles": {}}

        with patch.object(service._tracker, "_build_or_update_tile_index", side_effect=flaky_build) as mock_build:
            service.start_prewarm()
            for _ in range(50):
                if mock_build.call_count >= 2:
                    break
                time.sleep(0.05)

        assert calls == [TILE_ZOOM, SQUADRATINHO_ZOOM]

    def test_restart_prewarm_fires_again_after_single_fire_guard_tripped(self, service):
        """#576: restart_prewarm() must actually trigger a fresh pre-warm
        even after start_prewarm()'s single-fire guard has already tripped —
        the manual "clear coverage cache" action needs the next live
        request to hit a warm index, not pay for a synchronous rebuild."""
        service._tracker._activities_cache = []
        with patch.object(
            service._tracker, "_build_or_update_tile_index",
            return_value={"indexed_activity_ids": set(), "tiles": {}},
        ) as mock_build:
            service.start_prewarm()
            for _ in range(50):
                if mock_build.call_count >= 2:
                    break
                time.sleep(0.05)
            assert mock_build.call_count == 2

            service.restart_prewarm()
            for _ in range(50):
                if mock_build.call_count >= 4:
                    break
                time.sleep(0.05)

        assert mock_build.call_count == 4, "restart_prewarm() should have re-warmed both zooms"

    def test_prewarm_thread_is_a_daemon(self, service):
        service._tracker._activities_cache = []
        created_threads = []
        real_thread_cls = threading.Thread

        def spy_thread(*args, **kwargs):
            t = real_thread_cls(*args, **kwargs)
            created_threads.append(t)
            return t

        with patch("app.services.exploration_service.threading.Thread", side_effect=spy_thread):
            service.start_prewarm()
            for t in created_threads:
                t.join(timeout=5)

        assert len(created_threads) == 1
        assert created_threads[0].daemon is True


# ── verify_tile_claims (#493) ────────────────────────────────────


class TestVerifyTileClaims:
    """A planned route can claim a tile it never actually enters — e.g. its
    corner waypoint gets snapped by OSRM to a road running along the tile's
    boundary rather than through its interior. verify_tile_claims re-checks
    planned claims against the route's real coordinates."""

    def test_claims_tile_the_route_actually_enters(self, service):
        x, y = 4825, 6160
        south, west, north, east = tile_to_bounds(x, y, zoom=TILE_ZOOM)
        inside_lon = west + (east - west) * 0.5
        coordinates = [(south, inside_lon), (north, inside_lon)]

        result = service.verify_tile_claims(coordinates, [{"x": x, "y": y, "zoom": TILE_ZOOM}])

        assert result["status"] == "success"
        assert result["claimed"] == [{"x": x, "y": y, "zoom": TILE_ZOOM}]

    def test_does_not_claim_tile_the_route_only_skirts(self, service):
        """Regression for #493's reported bug: a route running along a tile's
        boundary (never entering it) must not be reported as claimed."""
        x, y = 4825, 6160
        south, west, north, east = tile_to_bounds(x, y, zoom=TILE_ZOOM)
        just_outside_lon = west - (east - west) * 0.001
        coordinates = [(south, just_outside_lon), (north, just_outside_lon)]

        result = service.verify_tile_claims(coordinates, [{"x": x, "y": y, "zoom": TILE_ZOOM}])

        assert result["status"] == "success"
        assert result["claimed"] == []

    def test_mixed_zooms_checked_independently(self, service):
        x14, y14 = lat_lon_to_tile(40.7128, -74.0060, zoom=TILE_ZOOM)
        south, west, north, east = tile_to_bounds(x14, y14, zoom=TILE_ZOOM)
        inside_lon = west + (east - west) * 0.5
        coordinates = [(south, inside_lon), (north, inside_lon)]

        # A squadratinho (zoom 17) tile far from this squadrat should not be claimed.
        result = service.verify_tile_claims(
            coordinates,
            [
                {"x": x14, "y": y14, "zoom": TILE_ZOOM},
                {"x": 0, "y": 0, "zoom": SQUADRATINHO_ZOOM},
            ],
        )

        assert result["status"] == "success"
        assert {"x": x14, "y": y14, "zoom": TILE_ZOOM} in result["claimed"]
        assert {"x": 0, "y": 0, "zoom": SQUADRATINHO_ZOOM} not in result["claimed"]


# ── find_new_tiles (#493 follow-up) ──────────────────────────────


class TestFindNewTiles:
    """Phase-2 distance refinement can carry a road route well outside the
    handful of tiles Phase-1 planned for (a detour to hit a distance target,
    a road-snap that wanders past the planned corner). find_new_tiles derives
    ground truth from the routed coordinates directly instead of checking a
    fixed candidate list, so those incidental tiles still get counted."""

    def test_fresh_route_reports_new_tiles_at_both_zooms(self, service):
        service._tracker._activities_cache = []
        x, y = 4825, 6160
        south, west, north, east = tile_to_bounds(x, y, zoom=TILE_ZOOM)
        inside_lon = west + (east - west) * 0.5
        coordinates = [(south, inside_lon), (north, inside_lon)]

        result = service.find_new_tiles(coordinates)

        assert result["status"] == "success"
        by_zoom = {entry["zoom"]: entry["tiles"] for entry in result["newTilesByZoom"]}
        assert TILE_ZOOM in by_zoom
        assert {"x": x, "y": y} in by_zoom[TILE_ZOOM]
        assert SQUADRATINHO_ZOOM in by_zoom  # the same line also crosses squadratinhos

    def test_already_ridden_tile_excluded(self, service):
        import polyline as codec

        x, y = 4825, 6160
        south, west, north, east = tile_to_bounds(x, y, zoom=TILE_ZOOM)
        inside_lon = west + (east - west) * 0.5
        coordinates = [(south, inside_lon), (north, inside_lon)]

        service._tracker._activities_cache = [{
            "id": 1,
            "polyline": codec.encode(coordinates),
            "start_date": "2026-01-01",
            "type": "Ride",
        }]

        result = service.find_new_tiles(coordinates)

        assert result["status"] == "success"
        by_zoom = {entry["zoom"]: entry["tiles"] for entry in result["newTilesByZoom"]}
        assert {"x": x, "y": y} not in by_zoom.get(TILE_ZOOM, [])

    def test_detour_far_outside_planned_area_still_counted(self, service):
        """The exact bug reported in #493 follow-up: a road-route detour
        (e.g. inserted by refineRoute to hit a distance target) lands in a
        tile nobody planned for. Unlike verify_tile_claims (which only
        checks a supplied candidate list), find_new_tiles must still report
        it since it derives tiles straight from the coordinates."""
        service._tracker._activities_cache = []
        x, y = 100, 200  # nowhere near any "planned" candidate
        south, west, north, east = tile_to_bounds(x, y, zoom=TILE_ZOOM)
        inside_lon = west + (east - west) * 0.5
        coordinates = [(south, inside_lon), (north, inside_lon)]

        result = service.find_new_tiles(coordinates)

        by_zoom = {entry["zoom"]: entry["tiles"] for entry in result["newTilesByZoom"]}
        assert {"x": x, "y": y} in by_zoom[TILE_ZOOM]


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
    """Tests for src/ors_client.get_route using a mocked shared session's post."""

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

        with patch("src.ors_client._session.post", return_value=mock_response) as mock_post:
            result = ors_client.get_route([[41.98, -87.65], [41.99, -87.64]], "cycling-regular", api_key="k")
        assert result is not None
        assert "features" in result
        mock_post.assert_called_once()

    def test_no_api_key_returns_none(self):
        from src import ors_client

        with patch("src.ors_client._session.post") as mock_post:
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="")
        assert result is None
        mock_post.assert_not_called()

    def test_timeout_returns_none(self):
        from src import ors_client

        with patch("src.ors_client._session.post", side_effect=requests.exceptions.Timeout()):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")
        assert result is None

    def test_network_error_returns_none(self):
        from src import ors_client

        with patch("src.ors_client._session.post", side_effect=requests.exceptions.ConnectionError("refused")):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")
        assert result is None

    def test_http_429_returns_rate_limited_sentinel(self):
        from src import ors_client

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("src.ors_client._session.post", return_value=mock_response):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")
        assert result is not None
        assert result.get("_ors_rate_limited") is True

    def test_unroutable_waypoint_returns_sentinel_with_coords(self):
        """ORS error 2010 returns _ors_unroutable list of (lon, lat) tuples."""
        from src import ors_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": {
                "code": 2010,
                "message": (
                    "Could not find routable point within a radius of 350.0 meters of "
                    "specified coordinate 1: -85.1439937 41.8041137."
                ),
            }
        }

        with patch("src.ors_client._session.post", return_value=mock_response):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")

        assert result is not None
        assert "_ors_unroutable" in result
        assert len(result["_ors_unroutable"]) == 1
        lon, lat = result["_ors_unroutable"][0]
        assert abs(lon - (-85.1439937)) < 1e-4
        assert abs(lat - 41.8041137) < 1e-4

    def test_unroutable_multiple_waypoints(self):
        """Multiple unroutable waypoints in one error message are all extracted."""
        from src import ors_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": {
                "code": 2010,
                "message": (
                    "Could not find routable point within a radius of 350.0 meters of "
                    "specified coordinate 0: -85.2979086 41.7549539.; "
                    "Could not find routable point within a radius of 350.0 meters of "
                    "specified coordinate 1: -85.1439937 41.8041137."
                ),
            }
        }

        with patch("src.ors_client._session.post", return_value=mock_response):
            result = ors_client.get_route([[0, 0], [1, 1]], "cycling-regular", api_key="k")

        assert result is not None
        assert len(result["_ors_unroutable"]) == 2


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

    def test_unroutable_interior_waypoint_is_dropped_and_retried(self, service_with_key):
        """When an interior waypoint is unroutable, it is dropped and ORS is retried."""
        good_raw = {
            "features": [{
                "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
                "properties": {
                    "summary": {"distance": 5000.0, "duration": 900.0},
                    "extras": {},
                },
            }],
        }
        # First call: interior waypoint [-85.14, 41.80] is unroutable.
        # Second call (after drop): succeeds.
        side_effects = [
            {"_ors_unroutable": [(-85.1439937, 41.8041137)]},
            good_raw,
        ]
        with patch("src.ors_client.get_route", side_effect=side_effects) as mock_ors:
            result = service_with_key.compute_route([
                [41.98, -87.65],            # start (routable)
                [41.8041137, -85.1439937],  # interior (off-road)
                [41.99, -87.64],            # end (routable)
            ])

        assert result["status"] == "success"
        assert mock_ors.call_count == 2
        # Second call must not include the bad interior waypoint.
        second_coords = mock_ors.call_args_list[1][0][0]
        assert len(second_coords) == 2  # only start + end

    def test_unroutable_start_cannot_be_dropped(self, service_with_key):
        """When the start (first) waypoint is unroutable, no retry is possible."""
        with patch("src.ors_client.get_route", return_value={"_ors_unroutable": [(-87.65, 41.98)]}):
            result = service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
        assert result["status"] == "error"

    def test_unroutable_retry_gives_up_gracefully_past_wall_clock_budget(self, service_with_key, mock_config):
        """The unroutable-waypoint retry loop must not hang the request thread
        indefinitely on a slow/degraded ORS endpoint (#freeze fix): once the
        overall wall-clock budget (exploration.ors_max_wait_seconds) is spent,
        compute_route returns a fast, clear error instead of continuing to
        retry ORS calls one after another.
        """
        def _get(key, default=None):
            if key == 'ors.api_key':
                return 'fake-key'
            if key == 'exploration.ors_max_wait_seconds':
                return 0  # budget already exhausted before the first retry check
            return default

        mock_config.get = MagicMock(side_effect=_get)

        # Every call reports a *different* unroutable interior waypoint so the
        # drop-and-retry loop would otherwise keep going indefinitely.
        side_effects = [
            {"_ors_unroutable": [(-85.14, 41.80)]},
            {"_ors_unroutable": [(-85.15, 41.81)]},
            {"_ors_unroutable": [(-85.16, 41.82)]},
        ]
        with patch("src.ors_client.get_route", side_effect=side_effects) as mock_ors:
            result = service_with_key.compute_route([
                [41.98, -87.65],
                [41.80, -85.14],
                [41.81, -85.15],
                [41.82, -85.16],
                [41.99, -87.64],
            ])

        assert result["status"] == "error"
        assert "too long" in result["message"].lower()
        # Only the initial call happened — the budget check stopped the loop
        # before a second retry, instead of grinding through every candidate.
        assert mock_ors.call_count == 1

    def test_first_ors_call_uses_budget_capped_timeout(self, service_with_key, mock_config):
        """#578: the *first* ORS call must use the wall-clock-budget-capped
        timeout (_budget_timeout()), same as every retry call below it —
        previously it used the fixed per-call ors_timeout_seconds instead,
        so a request that already spent most of its ors_max_wait_seconds
        budget (e.g. queueing behind the semaphore) could still let this
        first call run for a full fresh timeout, blowing past the overall
        budget compute_route() exists to enforce."""
        def _get(key, default=None):
            if key == 'ors.api_key':
                return 'fake-key'
            if key == 'exploration.ors_timeout_seconds':
                return 15
            if key == 'exploration.ors_max_wait_seconds':
                return 0.5  # much smaller than ors_timeout_seconds
            return default

        mock_config.get = MagicMock(side_effect=_get)

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
            result = service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])

        assert result["status"] == "success"
        first_call_timeout = mock_get.call_args_list[0].kwargs["timeout"]
        assert first_call_timeout <= 0.5, (
            f"first ORS call used timeout={first_call_timeout}, expected it capped to "
            "the ~0.5s wall-clock budget rather than the full 15s ors_timeout_seconds"
        )

    def test_concurrent_requests_bounded_by_semaphore(self, service_with_key):
        """compute_route calls run concurrently up to ors_max_concurrent_calls
        (default 2, since the fixture's mock config returns the caller's
        default for any key it doesn't special-case) — a call beyond that cap
        must queue rather than run, but legitimate concurrency within the cap
        (e.g. a "plot road route" click's short/long distance-target
        variants) should not serialize needlessly the way the old
        single-lock design did."""
        release_calls = threading.Event()
        concurrent_calls_seen = []
        in_flight = 0
        in_flight_lock = threading.Lock()

        good_raw = {
            "features": [{
                "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
                "properties": {
                    "summary": {"distance": 5000.0, "duration": 900.0},
                    "extras": {},
                },
            }],
        }

        def fake_get_route(coords, profile, api_key=None, timeout=15):
            nonlocal in_flight
            with in_flight_lock:
                in_flight += 1
                concurrent_calls_seen.append(in_flight)
            release_calls.wait(timeout=5)
            with in_flight_lock:
                in_flight -= 1
            return good_raw

        routes = [
            [[41.98, -87.65], [41.99, -87.64]],
            [[40.0, -80.0], [40.1, -80.1]],
            [[30.0, -90.0], [30.1, -90.1]],
        ]

        with patch("src.ors_client.get_route", side_effect=fake_get_route):
            threads = [
                threading.Thread(target=lambda r=r: service_with_key.compute_route(r))
                for r in routes
            ]
            for t in threads:
                t.start()

            # Give the two permitted slots time to actually reach ORS before
            # releasing them, so we observe the concurrency cap in effect.
            deadline = time.monotonic() + 5
            while in_flight < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert in_flight == 2, "expected exactly 2 concurrent ORS calls (the configured cap)"

            third_thread_still_waiting = not threads[2].join(timeout=0.3)

            release_calls.set()
            for t in threads:
                t.join(timeout=5)

        assert third_thread_still_waiting, "third request should have queued behind the first two"
        assert max(concurrent_calls_seen) == 2, "concurrency should have been capped at 2, not serialized to 1 or left unbounded"

    def test_busy_queue_returns_graceful_error_instead_of_hanging(self, service_with_key, mock_config):
        """If the wait for a semaphore slot alone would exceed the wall-clock
        budget, give up with a clear error rather than blocking the request
        thread indefinitely behind whatever's already in flight."""
        def _get(key, default=None):
            if key == 'ors.api_key':
                return 'fake-key'
            if key == 'exploration.ors_max_wait_seconds':
                return 0  # no time left to wait for a slot at all
            if key == 'exploration.ors_max_concurrent_calls':
                return 2
            return default

        mock_config.get = MagicMock(side_effect=_get)
        # Saturate both slots to simulate two other requests in flight.
        service_with_key._route_semaphore.acquire()
        service_with_key._route_semaphore.acquire()
        try:
            result = service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
        finally:
            service_with_key._route_semaphore.release()
            service_with_key._route_semaphore.release()

        assert result["status"] == "error"
        assert "busy" in result["message"].lower()

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

    def test_route_cache_evicts_expired_entries_on_write(self, service_with_key):
        """Expired memo entries must not accumulate forever (#482)."""
        raw = {
            "features": [{
                "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
                "properties": {
                    "summary": {"distance": 1000.0, "duration": 300.0},
                    "extras": {},
                },
            }],
        }
        with patch("src.ors_client.get_route", return_value=raw):
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
            assert len(service_with_key._route_cache) == 1

            # Expire the existing entry, then trigger another write.
            for k in list(service_with_key._route_cache.keys()):
                result, _ = service_with_key._route_cache[k]
                service_with_key._route_cache[k] = (result, time.monotonic() - 1)

            service_with_key.compute_route([[40.0, -80.0], [40.1, -80.1]])

        # The expired entry should have been evicted, leaving only the new one.
        assert len(service_with_key._route_cache) == 1

    def test_concurrent_cache_writes_do_not_raise(self, service_with_key):
        """#577: self._route_semaphore allows up to ors_max_concurrent_calls
        route computations to run at once, so concurrent
        _store_route_cache() calls (each doing an eviction scan over
        .items()/.keys()) could previously race and raise "dictionary
        changed size during iteration". Many distinct routes computed
        concurrently must not crash any worker thread."""
        raw = {
            "features": [{
                "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
                "properties": {
                    "summary": {"distance": 1000.0, "duration": 300.0},
                    "extras": {},
                },
            }],
        }
        errors = []

        def worker(i):
            try:
                service_with_key.compute_route([
                    [41.0, -87.0 - i * 0.001], [41.1, -87.1 - i * 0.001],
                ])
            except Exception as exc:  # pragma: no cover - failure path
                errors.append(exc)

        with patch("src.ors_client.get_route", return_value=raw):
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

        assert not errors, f"concurrent cache writes raised: {errors}"

    def test_route_cache_caps_total_entries(self, service_with_key):
        """Once over the cap, oldest entries are evicted rather than growing forever (#482)."""
        raw = {
            "features": [{
                "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
                "properties": {
                    "summary": {"distance": 1000.0, "duration": 300.0},
                    "extras": {},
                },
            }],
        }
        with patch("src.ors_client.get_route", return_value=raw):
            for i in range(MAX_ROUTE_CACHE_ENTRIES + 10):
                service_with_key.compute_route([[41.0, -87.0 - i * 0.001], [41.1, -87.1 - i * 0.001]])

        assert len(service_with_key._route_cache) == MAX_ROUTE_CACHE_ENTRIES


# ── Route cache disk persistence (#532) ───────────────────────────


class TestRouteCachePersistence:
    """The in-memory ORS route memo is lost on every process restart/redeploy,
    forcing identical requests to re-hit ORS's 2000/day free-tier quota cold.
    Persisting it to data/cache/route_cache.json makes the win survive
    restarts."""

    _RAW = {
        "features": [{
            "geometry": {"coordinates": [[-87.65, 41.98], [-87.64, 41.99]]},
            "properties": {
                "summary": {"distance": 1000.0, "duration": 300.0},
                "extras": {},
            },
        }],
    }

    def test_computed_route_is_written_to_disk(self, service_with_key):
        with patch("src.ors_client.get_route", return_value=self._RAW):
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
        # Persist now runs on a background thread (#573) rather than
        # synchronously inside compute_route().
        _wait_for_persist(service_with_key)

        cache_file = service_with_key._route_cache_path()
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert len(data["entries"]) == 1
        assert data["entries"][0]["profile"] == "cycling-regular"

    def test_persisted_cache_is_secured(self, service_with_key):
        """Cached route coordinates are GPS data — must be owner-only (0o600)."""
        with patch("src.ors_client.get_route", return_value=self._RAW):
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])

        with patch("app.services.exploration_service.secure_chmod") as mock_chmod:
            service_with_key._persist_route_cache()
        mock_chmod.assert_called()

    def test_load_from_disk_restores_cache_and_avoids_ors_call(self, service_with_key, mock_config, tmp_path):
        """A fresh ExplorationService instance (simulating a process restart)
        must reuse a still-valid on-disk cache instead of recomputing."""
        with patch("src.ors_client.get_route", return_value=self._RAW) as mock_get:
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
        assert mock_get.call_count == 1
        # Persist now runs on a background thread (#573) rather than
        # synchronously inside compute_route().
        _wait_for_persist(service_with_key)

        with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=mock_config):
            fresh = ExplorationService()
        fresh._tracker.cache_dir = tmp_path
        fresh._load_route_cache_from_disk()

        assert len(fresh._route_cache) == 1
        with patch("src.ors_client.get_route") as mock_get2:
            result = fresh.compute_route([[41.98, -87.65], [41.99, -87.64]])
        mock_get2.assert_not_called()
        assert result["status"] == "success"

    def test_expired_entries_are_not_loaded_from_disk(self, service_with_key, mock_config, tmp_path):
        cache_file = service_with_key._route_cache_path()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({
            "entries": [{
                "waypoints": [[41.98, -87.65], [41.99, -87.64]],
                "profile": "cycling-regular",
                "result": {"status": "success"},
                "expires_at": time.time() - 100,  # already expired
            }],
        }))

        with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=mock_config):
            fresh = ExplorationService()
        fresh._tracker.cache_dir = tmp_path
        fresh._load_route_cache_from_disk()

        assert len(fresh._route_cache) == 0

    def test_corrupt_cache_file_is_ignored(self, service_with_key, mock_config, tmp_path):
        cache_file = service_with_key._route_cache_path()
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("not valid json{")

        with patch('app.services.exploration_service.ConfigManager.get_instance', return_value=mock_config):
            fresh = ExplorationService()
        fresh._tracker.cache_dir = tmp_path
        fresh._load_route_cache_from_disk()  # must not raise

        assert len(fresh._route_cache) == 0

    def test_persist_does_not_block_semaphore_release(self, service_with_key):
        """#573: _persist_route_cache() must not run synchronously inside
        compute_route() while it still holds a _route_semaphore slot — a
        full-cache disk write there is I/O contention risk on a Pi's SD
        card, right inside an already-scarce (ors_max_concurrent_calls=2)
        critical section. Block the disk write and assert the semaphore slot
        is already released by the time compute_route() returns."""
        block_persist = threading.Event()
        real_persist = service_with_key._persist_route_cache

        def slow_persist():
            block_persist.wait(timeout=5)
            real_persist()

        with patch("src.ors_client.get_route", return_value=self._RAW), \
             patch.object(service_with_key, "_persist_route_cache", side_effect=slow_persist):
            service_with_key.compute_route([[41.98, -87.65], [41.99, -87.64]])
            # compute_route() returned already — if the persist were still
            # synchronous/inline this line would be unreachable until
            # block_persist is set, so getting here at all is the assertion.
            acquired = service_with_key._route_semaphore.acquire(timeout=1)
            assert acquired, "semaphore slot was not released — persist is still blocking it"
            service_with_key._route_semaphore.release()

            block_persist.set()
        _wait_for_persist(service_with_key)

    def test_bursty_writes_never_persist_concurrently(self, service_with_key):
        """Rapid successive route computations must coalesce onto whichever
        background writer is already running/about to run (#573), never run
        two disk writes at once. The on-disk cache should still end up with
        every route once things settle."""
        raw = self._RAW
        real_persist = service_with_key._persist_route_cache
        concurrent = 0
        max_concurrent = 0
        counter_lock = threading.Lock()

        def counted_persist():
            nonlocal concurrent, max_concurrent
            with counter_lock:
                concurrent += 1
                max_concurrent = max(max_concurrent, concurrent)
            try:
                real_persist()
            finally:
                with counter_lock:
                    concurrent -= 1

        with patch("src.ors_client.get_route", return_value=raw), \
             patch.object(service_with_key, "_persist_route_cache", side_effect=counted_persist):
            for i in range(5):
                service_with_key.compute_route([[41.0, -87.0 - i * 0.001], [41.1, -87.1 - i * 0.001]])
            # The debounce loop may sleep ROUTE_CACHE_PERSIST_DEBOUNCE_S
            # between coalesced writes if this burst outran the first write.
            _wait_for_persist(service_with_key, timeout=10)

        assert max_concurrent <= 1
        cache_file = service_with_key._route_cache_path()
        data = json.loads(cache_file.read_text())
        assert len(data["entries"]) == 5


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
        sb = ExplorationService._reduce_surface_extras(extras)
        assert sb["paved_pct"] == 50
        assert sb["unpaved_pct"] == 25
        assert sb["unknown_pct"] == 25

    def test_empty_extras(self):
        sb = ExplorationService._reduce_surface_extras({})
        assert sb == {"paved_pct": 0, "unpaved_pct": 0, "unknown_pct": 100}

    def test_weights_by_index_span_not_segment_count(self):
        """Regression for #483: a long unpaved stretch must outweigh a short paved connector."""
        extras = {
            "surface": {
                "values": [
                    [0, 2, 1],     # paved, span 2
                    [2, 402, 9],   # unpaved, span 400
                ]
            }
        }
        sb = ExplorationService._reduce_surface_extras(extras)
        assert sb["paved_pct"] == 0
        assert sb["unpaved_pct"] == 100


class TestIsOutAndBack:
    """#452: flag routes whose return leg substantially retraces the outbound leg."""

    def test_identical_retrace_is_out_and_back(self):
        outbound = [[40.0 + i * 0.001, -73.0] for i in range(10)]
        coordinates = outbound + list(reversed(outbound))
        assert ExplorationService._is_out_and_back(coordinates) is True

    def test_distinct_loop_corridors_not_out_and_back(self):
        # Outbound heads due north, return heads due east then south — no
        # shared corridor, so this should read as a genuine loop.
        outbound = [[40.0 + i * 0.001, -73.0] for i in range(10)]
        return_leg = [[40.009, -73.0 + i * 0.001] for i in range(1, 6)] + \
                     [[40.009 - i * 0.001, -72.995] for i in range(1, 6)]
        coordinates = outbound + return_leg
        assert ExplorationService._is_out_and_back(coordinates) is False

    def test_too_few_points_is_not_out_and_back(self):
        assert ExplorationService._is_out_and_back([[40.0, -73.0], [40.001, -73.0]]) is False

    def test_partial_overlap_below_threshold_not_flagged(self):
        # Only the first couple of return points land near the outbound leg;
        # most of the return leg diverges onto a different corridor.
        outbound = [[40.0 + i * 0.001, -73.0] for i in range(10)]
        return_leg = [[40.009, -73.0], [40.008, -73.0]] + \
                     [[40.0 + i * 0.001, -72.9] for i in range(8)]
        coordinates = outbound + return_leg
        assert ExplorationService._is_out_and_back(coordinates) is False
