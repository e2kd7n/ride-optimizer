"""
Exploration Service — wraps CoverageTracker for API consumption.

Provides tile coverage, road coverage, route computation via ORS, and cache
management following the existing service patterns (constructor + initialize).
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from src.config_manager import ConfigManager
from src.coverage_tracker import CoverageTracker

logger = logging.getLogger(__name__)

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


class ExplorationService:

    def __init__(self):
        self.config = ConfigManager.get_instance()
        self._tracker = CoverageTracker(self.config)
        # Route memoization: {(waypoints_key, profile): (result_dict, expires_at)}
        self._route_cache: Dict[tuple, Tuple[dict, float]] = {}

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

    def invalidate_caches(self):
        self._tracker.invalidate_caches()

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
        from src import ors_client

        profile = _SURFACE_TO_PROFILE.get(surface_preference, "cycling-regular")
        api_key = self.config.get("ors.api_key", "")
        timeout = int(self.config.get("exploration.ors_timeout_seconds", 15))
        ttl = int(self.config.get("exploration.route_cache_ttl_seconds", 600))

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

        # ORS expects [lon, lat] pairs.
        ors_coords = [[lon, lat] for lat, lon in waypoints]
        raw = ors_client.get_route(ors_coords, profile, api_key=api_key, timeout=timeout)

        # Preferred profile not enabled on this account — fall back to cycling-regular.
        if raw is not None and raw.get("_ors_profile_unavailable") and profile != "cycling-regular":
            logger.info("Profile %s unavailable, falling back to cycling-regular", profile)
            profile = "cycling-regular"
            raw = ors_client.get_route(ors_coords, profile, api_key=api_key, timeout=timeout)

        # Unroutable waypoints: drop every interior bad waypoint and retry.
        # "Interior" = not the first (start) or last (end) coordinate.
        # We identify bad waypoints by their [lon, lat] coordinates, not by
        # index, because ORS index numbering can vary across versions.
        # Retry until no interior waypoints remain to drop (guard against loops).
        _drop_attempts = 0
        while raw is not None and raw.get("_ors_unroutable"):
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
            raw = ors_client.get_route(ors_coords, profile, api_key=api_key, timeout=timeout)

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

        self._route_cache[cache_key] = (result, time.monotonic() + ttl)
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

        surface_breakdown = ExplorationService._reduce_surface_extras(
            props.get("extras", {}), summary["distance"]
        )

        return {
            "status": "success",
            "coordinates": coordinates,
            "distance_km": distance_km,
            "duration_min": duration_min,
            "surface_breakdown": surface_breakdown,
        }

    @staticmethod
    def _reduce_surface_extras(extras: dict, total_distance_m: float) -> Dict[str, Any]:
        """Reduce ORS extras.surface segment array into paved/unpaved/unknown percentages."""
        surface_values = (extras.get("surface") or {}).get("values", [])

        paved_m = 0.0
        unpaved_m = 0.0
        unknown_m = 0.0

        for segment in surface_values:
            # Each entry: [from_idx, to_idx, surface_value]
            if len(segment) < 3:
                continue
            _, _, value = segment[:3]
            # Distance isn't provided per-segment in ORS v2; we approximate using
            # the proportion of segments (ORS surface.values covers the full route).
            # If total is 0, skip.
            if total_distance_m <= 0:
                continue
            if value in _PAVED_SURFACE_VALUES:
                paved_m += 1
            elif value in _UNPAVED_SURFACE_VALUES:
                unpaved_m += 1
            else:
                unknown_m += 1

        total_segments = paved_m + unpaved_m + unknown_m
        if total_segments == 0:
            return {"paved_pct": 0, "unpaved_pct": 0, "unknown_pct": 100}

        return {
            "paved_pct": round(paved_m / total_segments * 100),
            "unpaved_pct": round(unpaved_m / total_segments * 100),
            "unknown_pct": round(unknown_m / total_segments * 100),
        }
