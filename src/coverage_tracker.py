"""
Coverage tracking for exploration route generation.

Computes which map tiles and road segments have been ridden
based on cached Strava activity GPS tracks.
"""

import json
import hashlib
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import polyline as polyline_codec

logger = logging.getLogger(__name__)

TILE_ZOOM = 14
INTERPOLATION_INTERVAL_M = 80
EARTH_RADIUS_M = 6_371_000


@dataclass
class TileCoverage:
    """Result of tile coverage computation."""
    visited: Dict[str, dict] = field(default_factory=dict)
    total_in_bounds: int = 0
    bounds: Optional[Tuple[float, float, float, float]] = None
    computed_at: str = ""

    @property
    def visited_count(self) -> int:
        return len(self.visited)

    @property
    def coverage_pct(self) -> float:
        if self.total_in_bounds == 0:
            return 0.0
        return round(self.visited_count / self.total_in_bounds * 100, 1)

    def to_dict(self) -> dict:
        return {
            "visited": self.visited,
            "total_in_bounds": self.total_in_bounds,
            "visited_count": self.visited_count,
            "coverage_pct": self.coverage_pct,
            "bounds": self.bounds,
            "computed_at": self.computed_at,
        }


def lat_lon_to_tile(lat: float, lon: float, zoom: int = TILE_ZOOM) -> Tuple[int, int]:
    """Convert latitude/longitude to slippy-map tile indices."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_bounds(x: int, y: int, zoom: int = TILE_ZOOM) -> Tuple[float, float, float, float]:
    """Convert tile indices to (south, west, north, east) bounds in degrees."""
    n = 2 ** zoom
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    south_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    north = math.degrees(north_rad)
    south = math.degrees(south_rad)
    return south, west, north, east


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two points."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _interpolate_points(
    coords: List[Tuple[float, float]], interval_m: float = INTERPOLATION_INTERVAL_M
) -> List[Tuple[float, float]]:
    """
    Fill in points along a polyline so no gap exceeds *interval_m* metres.

    Prevents tile-skipping when summary polylines have sparse GPS points.
    """
    if len(coords) < 2:
        return list(coords)

    result: List[Tuple[float, float]] = [coords[0]]
    for i in range(1, len(coords)):
        lat1, lon1 = coords[i - 1]
        lat2, lon2 = coords[i]
        seg_dist = _haversine_m(lat1, lon1, lat2, lon2)
        if seg_dist > interval_m:
            steps = int(math.ceil(seg_dist / interval_m))
            for s in range(1, steps):
                frac = s / steps
                result.append((lat1 + frac * (lat2 - lat1), lon1 + frac * (lon2 - lon1)))
        result.append((lat2, lon2))
    return result


def _bounds_key(bounds: Tuple[float, float, float, float]) -> str:
    """Deterministic cache key for a bounding box."""
    rounded = tuple(round(v, 4) for v in bounds)
    return hashlib.md5(str(rounded).encode()).hexdigest()[:12]


class CoverageTracker:
    """Compute tile and road coverage from Strava activity GPS data."""

    def __init__(self, config):
        self.config = config
        self.zoom = config.get("exploration.tile_zoom_level", TILE_ZOOM)
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._activities_cache: Optional[List[dict]] = None

    # ------------------------------------------------------------------
    # Activity loading
    # ------------------------------------------------------------------

    def _load_activities(self) -> List[dict]:
        """Load cached Strava activities (lazy, cached in memory per request)."""
        if self._activities_cache is not None:
            return self._activities_cache

        path = Path("data/cache/activities.json")
        if not path.exists():
            logger.warning("No activities cache found at %s", path)
            self._activities_cache = []
            return self._activities_cache

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            activities = data if isinstance(data, list) else data.get("activities", [])
            ride_types = {"Ride", "EBikeRide", "GravelRide", "MountainBikeRide"}
            activities = [
                a for a in activities
                if a.get("type") in ride_types or a.get("sport_type") in ride_types
            ]
            logger.info("Loaded %d ride activities for coverage analysis", len(activities))
            self._activities_cache = activities
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load activities: %s", exc)
            self._activities_cache = []

        return self._activities_cache

    def _decode_activity_coords(self, activity: dict) -> List[Tuple[float, float]]:
        """Decode an activity's polyline to a list of (lat, lon) tuples."""
        encoded = activity.get("polyline")
        if not encoded:
            return []
        try:
            return polyline_codec.decode(encoded)
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Tile coverage
    # ------------------------------------------------------------------

    def get_tile_coverage(
        self,
        bounds: Tuple[float, float, float, float],
    ) -> TileCoverage:
        """
        Compute tile coverage within a bounding box.

        Args:
            bounds: (south, west, north, east) in degrees

        Returns:
            TileCoverage with visited tile data and stats
        """
        cache_path = self.cache_dir / f"coverage_tiles_{_bounds_key(bounds)}.json"
        cached = self._load_tile_cache(cache_path)
        if cached is not None:
            return cached

        south, west, north, east = bounds
        activities = self._load_activities()

        visited: Dict[str, dict] = {}

        for act in activities:
            coords = self._decode_activity_coords(act)
            if not coords:
                continue

            start = act.get("start_latlng")
            if start:
                slat, slon = start
                if slat < south - 0.1 or slat > north + 0.1 or slon < west - 0.1 or slon > east + 0.1:
                    end = act.get("end_latlng")
                    if end:
                        elat, elon = end
                        if elat < south - 0.1 or elat > north + 0.1 or elon < west - 0.1 or elon > east + 0.1:
                            continue

            interpolated = _interpolate_points(coords)
            act_id = act.get("id")
            act_date = act.get("start_date", "")

            for lat, lon in interpolated:
                if lat < south or lat > north or lon < west or lon > east:
                    continue
                tx, ty = lat_lon_to_tile(lat, lon, self.zoom)
                key = f"{tx},{ty}"
                if key not in visited:
                    visited[key] = {
                        "first_ridden": act_date,
                        "activity_ids": [act_id],
                    }
                elif act_id not in visited[key]["activity_ids"]:
                    visited[key]["activity_ids"].append(act_id)

        min_tx, min_ty = lat_lon_to_tile(north, west, self.zoom)
        max_tx, max_ty = lat_lon_to_tile(south, east, self.zoom)
        total_tiles = (max_tx - min_tx + 1) * (max_ty - min_ty + 1)

        result = TileCoverage(
            visited=visited,
            total_in_bounds=max(total_tiles, 1),
            bounds=bounds,
            computed_at=datetime.utcnow().isoformat(),
        )

        self._save_tile_cache(cache_path, result)
        return result

    def get_tile_coverage_all(self) -> TileCoverage:
        """
        Compute tile coverage across ALL activities (no bounds filter).

        Useful for getting overall stats and the full visited tile set.
        """
        activities = self._load_activities()
        visited: Dict[str, dict] = {}

        for act in activities:
            coords = self._decode_activity_coords(act)
            if not coords:
                continue

            interpolated = _interpolate_points(coords)
            act_id = act.get("id")
            act_date = act.get("start_date", "")

            for lat, lon in interpolated:
                tx, ty = lat_lon_to_tile(lat, lon, self.zoom)
                key = f"{tx},{ty}"
                if key not in visited:
                    visited[key] = {
                        "first_ridden": act_date,
                        "activity_ids": [act_id],
                    }
                elif act_id not in visited[key]["activity_ids"]:
                    visited[key]["activity_ids"].append(act_id)

        return TileCoverage(
            visited=visited,
            total_in_bounds=len(visited),
            bounds=None,
            computed_at=datetime.utcnow().isoformat(),
        )

    # ------------------------------------------------------------------
    # Road coverage (Phase 1B — osmnx-based map matching)
    # ------------------------------------------------------------------

    def get_road_coverage(
        self,
        bounds: Tuple[float, float, float, float],
    ) -> dict:
        """
        Compute road coverage within a bounding box using OSM data.

        Requires osmnx and shapely. Falls back gracefully if unavailable.
        """
        try:
            import osmnx as ox
            from shapely.geometry import LineString, Point
            from shapely.strtree import STRtree
        except ImportError:
            logger.warning("osmnx/shapely not installed — road coverage unavailable")
            return {"status": "error", "message": "Road coverage requires osmnx and shapely"}

        south, west, north, east = bounds
        graph_cache = self.cache_dir / "road_network.graphml"

        if graph_cache.exists():
            try:
                G = ox.load_graphml(graph_cache)
                logger.info("Loaded cached road network from %s", graph_cache)
            except Exception:
                G = None
        else:
            G = None

        if G is None:
            logger.info("Fetching road network from OSM for bounds %s", bounds)
            try:
                G = ox.graph_from_bbox(
                    bbox=(north, south, east, west),
                    network_type="bike",
                    simplify=True,
                )
                ox.save_graphml(G, graph_cache)
            except Exception as exc:
                logger.error("Failed to fetch road network: %s", exc)
                return {"status": "error", "message": str(exc)}

        edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        snap_tolerance = self.config.get("exploration.snap_tolerance_meters", 30)
        snap_deg = snap_tolerance / 111_000

        edge_geoms = []
        edge_keys = []
        for idx, row in edges.iterrows():
            geom = row.get("geometry")
            if geom is not None:
                edge_geoms.append(geom)
                edge_keys.append(idx)

        tree = STRtree(edge_geoms)
        ridden_set: Set[int] = set()

        activities = self._load_activities()
        for act in activities:
            coords = self._decode_activity_coords(act)
            if not coords:
                continue
            interpolated = _interpolate_points(coords)
            for lat, lon in interpolated:
                if lat < south or lat > north or lon < west or lon > east:
                    continue
                pt = Point(lon, lat)
                nearest_idx = tree.nearest(pt)
                nearest_geom = edge_geoms[nearest_idx]
                if pt.distance(nearest_geom) <= snap_deg:
                    ridden_set.add(nearest_idx)

        ridden_edges = []
        unridden_edges = []
        for i, geom in enumerate(edge_geoms):
            coords_list = list(geom.coords)
            edge_data = {
                "coordinates": [(lat, lon) for lon, lat in coords_list],
                "length_m": edges.iloc[i].get("length", 0),
            }
            if i in ridden_set:
                ridden_edges.append(edge_data)
            else:
                unridden_edges.append(edge_data)

        total = len(edge_geoms)
        ridden_count = len(ridden_set)
        return {
            "status": "success",
            "ridden": ridden_edges,
            "unridden": unridden_edges,
            "stats": {
                "total_edges": total,
                "ridden_edges": ridden_count,
                "unridden_edges": total - ridden_count,
                "coverage_pct": round(ridden_count / max(total, 1) * 100, 1),
            },
            "bounds": bounds,
            "computed_at": datetime.utcnow().isoformat(),
        }

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _load_tile_cache(self, path: Path) -> Optional[TileCoverage]:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TileCoverage(
                visited=data["visited"],
                total_in_bounds=data["total_in_bounds"],
                bounds=tuple(data["bounds"]) if data.get("bounds") else None,
                computed_at=data.get("computed_at", ""),
            )
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _save_tile_cache(self, path: Path, coverage: TileCoverage) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(coverage.to_dict(), f)
        except OSError as exc:
            logger.warning("Failed to write tile cache: %s", exc)

    def invalidate_caches(self) -> None:
        """Remove all coverage caches (call after new activities are fetched)."""
        self._activities_cache = None
        for p in self.cache_dir.glob("coverage_tiles_*.json"):
            try:
                p.unlink()
            except OSError:
                pass
        graph_cache = self.cache_dir / "road_network.graphml"
        if graph_cache.exists():
            try:
                graph_cache.unlink()
            except OSError:
                pass
        logger.info("Coverage caches invalidated")
