"""
Exploration Service — wraps CoverageTracker for API consumption.

Provides tile coverage, road coverage, route computation via ORS, and cache
management following the existing service patterns (constructor + initialize).
"""

from src.secure_logger import SecureLogger
import math
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from src.config_manager import ConfigManager
from src.coverage_tracker import CoverageTracker

logger = SecureLogger(__name__)

# Maps the frontend surface_preference value to an ORS cycling profile.
_SURFACE_TO_PROFILE = {
    "paved": "cycling-road",
    "unpaved": "cycling-mountain",
    "any": "cycling-regular",
}

# ORS surface-value categories used in extras.surface segments.
_PAVED_SURFACE_VALUES = {0, 1, 2, 3, 4, 5, 6}    # asphalt, concrete, paved, ...
_UNPAVED_SURFACE_VALUES = {7, 8, 9, 10, 11, 12}   # gravel, dirt, grass, ...
# Values outside both sets are treated as unknown.

# Cap on retained route-memo entries (#482) — each entry holds a full route
# polyline, so an unbounded dict is a slow memory leak on a long-running Pi.
MAX_ROUTE_CACHE_ENTRIES = 200


class ExplorationService:

    def __init__(self):
        self.config = ConfigManager.get_instance()
        self._tracker = CoverageTracker(self.config)
        # Route memoization: {(waypoints_key, profile): (result_dict, expires_at)}
        self._route_cache: Dict[tuple, Tuple[dict, float]] = {}
        # Serializes ORS "plot road route" calls (#compute_route) — only one
        # runs at a time. Running them concurrently was the other half of the
        # thread-starvation freeze: each already burns up to ors_max_wait_seconds
        # of a gunicorn thread, so a handful of simultaneous requests could tie
        # up every thread (and ORS's own per-minute quota) at once. Queueing
        # them serially trades that for a bounded wait per request instead.
        self._route_lock = threading.Lock()

    def initialize(self):
        pass

    def get_tile_coverage(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            result = self._tracker.get_tile_coverage(bounds, zoom=zoom)
            return {"status": "success", **result.to_dict()}
        except Exception as exc:
            logger.error("Tile coverage failed: %s", exc, exc_info=True)
            return {"status": "error", "message": str(exc)}

    def get_tile_coverage_all(self, zoom: Optional[int] = None) -> Dict[str, Any]:
        try:
            result = self._tracker.get_tile_coverage_all(zoom=zoom)
            return {"status": "success", **result.to_dict()}
        except Exception as exc:
            logger.error("Full tile coverage failed: %s", exc, exc_info=True)
            return {"status": "error", "message": str(exc)}

    def get_road_coverage(
        self,
        bounds: Tuple[float, float, float, float],
    ) -> Dict[str, Any]:
        return self._tracker.get_road_coverage(bounds)

    def get_roadless_tiles(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._tracker.get_roadless_tiles(bounds, zoom=zoom)

    def invalidate_caches(self):
        self._tracker.invalidate_caches()

    def _store_route_cache(self, cache_key: tuple, result: dict, expires_at: float) -> None:
        """Store a route memo entry, evicting expired entries first and then
        the oldest entries if still over the cap (#482)."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._route_cache.items() if exp <= now]
        for k in expired:
            del self._route_cache[k]

        self._route_cache[cache_key] = (result, expires_at)

        if len(self._route_cache) > MAX_ROUTE_CACHE_ENTRIES:
            # dicts preserve insertion order — oldest entries were inserted first.
            overflow = len(self._route_cache) - MAX_ROUTE_CACHE_ENTRIES
            for k in list(self._route_cache.keys())[:overflow]:
                del self._route_cache[k]

    def verify_tile_claims(
        self,
        coordinates: List[Tuple[float, float]],
        tiles: List[Dict[str, int]],
    ) -> Dict[str, Any]:
        """Check which of the given tiles a route's actual polyline crosses.

        `tiles` targets are only speculative until the road-following route
        is known (a planned "claim" corner may end up snapped to a road that
        never actually enters the tile). This runs the same exact tile-
        crossing math used to score recorded activities against a planned
        route's real coordinates, so the UI can highlight only tiles that
        are genuinely reachable rather than ones a route merely aimed at.
        """
        by_zoom: Dict[int, set] = {}
        for t in tiles:
            by_zoom.setdefault(t["zoom"], set()).add((t["x"], t["y"]))

        claimed: List[Dict[str, int]] = []
        for zoom, wanted in by_zoom.items():
            crossed = self._tracker.tiles_crossed_by_path(coordinates, zoom)
            for x, y in wanted:
                if (x, y) in crossed:
                    claimed.append({"x": x, "y": y, "zoom": zoom})

        return {"status": "success", "claimed": claimed}

    def find_new_tiles(self, coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Find every tile a route's real polyline crosses that isn't
        already covered by a past activity, at both squadrat and
        squadratinho granularity.

        Phase-1 route planning only aims at a handful of candidate tiles
        chosen from a straight-line heuristic; Phase-2 distance refinement
        (`refineRoute` in explore.js) can then snap the route to roads or
        insert padding waypoints that carry it well outside that planned
        set (#493 follow-up). Checking the planned list alone under-reports
        new tiles whenever the real route diverges from the plan, so this
        instead derives ground truth straight from the routed coordinates.
        """
        from src.coverage_tracker import TILE_ZOOM, SQUADRATINHO_ZOOM

        new_tiles_by_zoom: List[Dict[str, Any]] = []
        for zoom in (TILE_ZOOM, SQUADRATINHO_ZOOM):
            crossed = self._tracker.tiles_crossed_by_path(coordinates, zoom)
            # Use the all-activities coverage (one cache file per zoom, shared
            # across every route) rather than a per-request bounds query —
            # bounds computed from each route's own coordinates would give
            # get_tile_coverage() a near-unique cache key on every call,
            # writing an unbounded number of never-expiring cache files.
            # Let a coverage lookup failure propagate rather than treating it
            # as "nothing visited" — that would report already-ridden tiles
            # as new. Callers (exploration_verify_tiles route, explore.js)
            # already treat a failed request as "couldn't verify" and leave
            # the Phase-1 preview alone rather than trusting a false claim.
            coverage = self._tracker.get_tile_coverage_all(zoom=zoom)
            visited = {tuple(int(v) for v in key.split(",")) for key in coverage.visited}

            new_tiles = crossed - visited
            if new_tiles:
                new_tiles_by_zoom.append({
                    "zoom": zoom,
                    "tiles": [{"x": x, "y": y} for x, y in sorted(new_tiles)],
                })

        return {"status": "success", "newTilesByZoom": new_tiles_by_zoom}

    # ── ORS road routing ─────────────────────────────────────────

    def compute_route(
        self,
        waypoints: List[Tuple[float, float]],
        surface_preference: str = "any",
    ) -> Dict[str, Any]:
        """Compute a road-following route via ORS for the given waypoints.

        Args:
            waypoints: List of (lat, lon) pairs.
            surface_preference: ``"any"`` | ``"paved"`` | ``"unpaved"``.

        Returns:
            Dict with ``status``, and on success:
            ``coordinates`` (list of [lat, lon]),
            ``distance_km``, ``duration_min``, ``surface_breakdown``.
        """
        profile = _SURFACE_TO_PROFILE.get(surface_preference, "cycling-regular")
        api_key = self.config.get("ors.api_key", "")
        ttl = int(self.config.get("exploration.route_cache_ttl_seconds", 600))
        # Hard wall-clock budget for this call, across queueing behind any
        # in-flight request (below) AND every retry/fallback ORS attempt.
        # Without this, the unroutable-waypoint retry loop (up to 10
        # iterations) could each wait up to ors_timeout_seconds, tying up a
        # gunicorn thread for minutes on a slow/degraded ORS endpoint — with
        # only 4 threads (gunicorn.conf.py), a couple of concurrent
        # point-to-point requests were enough to starve the whole app for
        # every user, not just the one waiting on ORS.
        max_wait = float(self.config.get("exploration.ors_max_wait_seconds", 40))
        deadline = time.monotonic() + max_wait

        if not api_key:
            return {
                "status": "error",
                "message": "Road routing is not configured (ORS_API_KEY missing)",
            }

        # Memoization key — waypoints as a tuple of pairs + profile.
        cache_key = (tuple((round(lat, 6), round(lon, 6)) for lat, lon in waypoints), profile)
        cached = self._route_cache.get(cache_key)
        if cached is not None:
            result, expires_at = cached
            if time.monotonic() < expires_at:
                logger.debug("ORS cache hit for key %s", cache_key)
                return result

        # Only one "plot road route" computation runs at a time (see
        # self._route_lock) — concurrent ORS calls were the other half of the
        # thread-starvation freeze. Queue behind whichever request got there
        # first rather than racing it; give up gracefully if the queue wait
        # alone would blow the overall budget.
        if not self._route_lock.acquire(timeout=max(0.0, deadline - time.monotonic())):
            return {
                "status": "error",
                "message": "Road routing is busy with another request — try again shortly",
            }
        try:
            # Another request may have computed (and cached) this exact
            # route while we were waiting for the lock.
            cached = self._route_cache.get(cache_key)
            if cached is not None:
                result, expires_at = cached
                if time.monotonic() < expires_at:
                    logger.debug("ORS cache hit for key %s (post-queue)", cache_key)
                    return result
            return self._compute_route_via_ors(waypoints, profile, api_key, ttl, deadline, max_wait, cache_key)
        finally:
            self._route_lock.release()

    def _compute_route_via_ors(
        self,
        waypoints: List[Tuple[float, float]],
        profile: str,
        api_key: str,
        ttl: int,
        deadline: float,
        max_wait: float,
        cache_key: tuple,
    ) -> Dict[str, Any]:
        """Run the actual ORS call(s) for compute_route, holding self._route_lock."""
        from src import ors_client

        timeout = int(self.config.get("exploration.ors_timeout_seconds", 15))

        def _budget_timeout() -> float:
            """Per-call timeout capped to whatever's left of the overall budget."""
            return max(0.0, min(timeout, deadline - time.monotonic()))

        # ORS expects [lon, lat] pairs.
        ors_coords = [[lon, lat] for lat, lon in waypoints]
        raw = ors_client.get_route(ors_coords, profile, api_key=api_key, timeout=timeout)

        # Preferred profile not enabled on this account — fall back to cycling-regular.
        if (
            raw is not None
            and raw.get("_ors_profile_unavailable")
            and profile != "cycling-regular"
            and time.monotonic() < deadline
        ):
            logger.info("Profile %s unavailable, falling back to cycling-regular", profile)
            profile = "cycling-regular"
            raw = ors_client.get_route(ors_coords, profile, api_key=api_key, timeout=_budget_timeout())

        # Unroutable waypoints: drop every interior bad waypoint and retry.
        # "Interior" = not the first (start) or last (end) coordinate.
        # We identify bad waypoints by their [lon, lat] coordinates, not by
        # index, because ORS index numbering can vary across versions.
        # Retry until no interior waypoints remain to drop (guard against loops).
        _drop_attempts = 0
        _timed_out = False
        while raw is not None and raw.get("_ors_unroutable"):
            if time.monotonic() >= deadline:
                _timed_out = True
                break
            bad_coords = {(round(lon, 4), round(lat, 4)) for lon, lat in raw["_ors_unroutable"]}
            # Only drop interior points (preserve first and last).
            interior = ors_coords[1:-1]
            pruned = [c for c in interior if (round(c[0], 4), round(c[1], 4)) not in bad_coords]
            if len(pruned) == len(interior):
                # None of the bad coords matched an interior waypoint — can't fix.
                break
            ors_coords = [ors_coords[0]] + pruned + [ors_coords[-1]]
            logger.info(
                "Dropped %d unroutable interior waypoint(s); retrying with %d coords",
                len(interior) - len(pruned), len(ors_coords),
            )
            _drop_attempts += 1
            if len(ors_coords) < 2 or _drop_attempts > 10:
                break
            # Re-check cache for the pruned list.
            cache_key = (
                tuple((round(c[1], 6), round(c[0], 6)) for c in ors_coords),
                profile,
            )
            cached = self._route_cache.get(cache_key)
            if cached is not None:
                result, expires_at = cached
                if time.monotonic() < expires_at:
                    return result
            raw = ors_client.get_route(ors_coords, profile, api_key=api_key, timeout=_budget_timeout())

        if _timed_out:
            logger.warning("ORS route computation exceeded %.0fs budget; giving up gracefully", max_wait)
            return {
                "status": "error",
                "message": "Road routing is taking too long — try again, or a shorter/simpler route",
            }
        if raw is None:
            return {"status": "error", "message": "Road routing request failed"}
        if raw.get("_ors_rate_limited"):
            return {
                "status": "error",
                "message": "Road routing rate limit reached — try again shortly",
            }
        if raw.get("_ors_unroutable") is not None:
            return {"status": "error", "message": "Road routing failed: no routable path near waypoints"}

        try:
            result = self._parse_ors_response(raw)
        except Exception as exc:
            logger.error("Failed to parse ORS response: %s", exc, exc_info=True)
            return {"status": "error", "message": "Unexpected ORS response format"}

        self._store_route_cache(cache_key, result, time.monotonic() + ttl)
        return result

    # ── helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_ors_response(raw: dict) -> Dict[str, Any]:
        """Extract coordinates, distance, duration, and surface breakdown."""
        feature = raw["features"][0]
        props = feature["properties"]
        summary = props["summary"]
        geom = feature["geometry"]

        # Coordinates come back as [lon, lat] from ORS; flip to [lat, lon].
        coordinates = [[lat, lon] for lon, lat in geom["coordinates"]]

        distance_km = round(summary["distance"] / 1000, 2)
        duration_min = round(summary["duration"] / 60, 1)

        surface_breakdown = ExplorationService._reduce_surface_extras(props.get("extras", {}))
        is_out_and_back = ExplorationService._is_out_and_back(coordinates)

        return {
            "status": "success",
            "coordinates": coordinates,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "surface_breakdown": surface_breakdown,
            "is_out_and_back": is_out_and_back,
        }

    # Fraction of return-leg points that must fall within OUT_AND_BACK_RADIUS_M
    # of some outbound-leg point for the route to be flagged as out-and-back (#452).
    OUT_AND_BACK_OVERLAP_THRESHOLD = 0.7
    OUT_AND_BACK_RADIUS_M = 150

    @staticmethod
    def _is_out_and_back(coordinates: List[List[float]]) -> bool:
        """Detect a route whose return leg substantially retraces its outbound leg.

        Splits the polyline in half and checks what fraction of return-leg
        points land within ~150m of some outbound-leg point. Real road
        geometry rarely retraces exactly, so this is a proximity match against
        the whole outbound half rather than a point-by-point mirror check —
        that's what lets a genuine loop (distinct corridors both ways) read as
        low-overlap even if the two halves end up near each other briefly.
        """
        if len(coordinates) < 4:
            return False

        mid = len(coordinates) // 2
        outbound, return_leg = coordinates[:mid], coordinates[mid:]
        if not outbound or not return_leg:
            return False

        # Coarse degrees-per-meter conversion is fine at the ~150m scale this
        # threshold operates at — no need for full haversine per point pair.
        lat_ref = coordinates[0][0]
        deg_per_m_lat = 1 / 111_320
        deg_per_m_lon = 1 / (111_320 * max(0.01, abs(math.cos(math.radians(lat_ref)))))
        radius_deg_lat = ExplorationService.OUT_AND_BACK_RADIUS_M * deg_per_m_lat
        radius_deg_lon = ExplorationService.OUT_AND_BACK_RADIUS_M * deg_per_m_lon

        near_count = 0
        for r_lat, r_lon in return_leg:
            for o_lat, o_lon in outbound:
                if abs(r_lat - o_lat) <= radius_deg_lat and abs(r_lon - o_lon) <= radius_deg_lon:
                    near_count += 1
                    break

        return (near_count / len(return_leg)) >= ExplorationService.OUT_AND_BACK_OVERLAP_THRESHOLD

    @staticmethod
    def _reduce_surface_extras(extras: dict) -> Dict[str, Any]:
        """Reduce ORS extras.surface segment array into paved/unpaved/unknown percentages."""
        surface_values = (extras.get("surface") or {}).get("values", [])

        paved_m = 0.0
        unpaved_m = 0.0
        unknown_m = 0.0

        for segment in surface_values:
            # Each entry: [from_idx, to_idx, surface_value]
            if len(segment) < 3:
                continue
            from_idx, to_idx, value = segment[:3]
            # Distance per segment isn't provided in ORS v2, but the coordinate
            # index span is a good proxy for how much of the route it covers.
            span = to_idx - from_idx
            if value in _PAVED_SURFACE_VALUES:
                paved_m += span
            elif value in _UNPAVED_SURFACE_VALUES:
                unpaved_m += span
            else:
                unknown_m += span

        total_span = paved_m + unpaved_m + unknown_m
        if total_span == 0:
            return {"paved_pct": 0, "unpaved_pct": 0, "unknown_pct": 100}

        return {
            "paved_pct": round(paved_m / total_span * 100),
            "unpaved_pct": round(unpaved_m / total_span * 100),
            "unknown_pct": round(unknown_m / total_span * 100),
        }
