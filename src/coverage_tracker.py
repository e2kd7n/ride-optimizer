"""
Coverage tracking for exploration route generation.

Computes which map tiles and road segments have been ridden
based on cached Strava activity GPS tracks.
"""

import json
import hashlib
from src.secure_logger import SecureLogger
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import polyline as polyline_codec
import requests

from src.json_storage import secure_chmod

logger = SecureLogger(__name__)

TILE_ZOOM = 14              # "squadrat" granularity (squadrat.at / squadrat.com default)
SQUADRATINHO_ZOOM = 17      # "squadratinho" granularity — each squadrat = 8x8 squadratinhos
INTERPOLATION_INTERVAL_M = 80
EARTH_RADIUS_M = 6_371_000
MAX_ROAD_NETWORK_CACHES = 20  # cap on retained road_network_<hash>.graphml files
MAX_WATER_POLYGON_CACHES = 20  # cap on retained water_<hash>.json files
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"


@dataclass
class TileCoverage:
    """Result of tile coverage computation."""
    visited: Dict[str, dict] = field(default_factory=dict)
    total_in_bounds: int = 0
    bounds: Optional[Tuple[float, float, float, float]] = None
    computed_at: str = ""
    zoom: int = TILE_ZOOM

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
            "zoom": self.zoom,
        }


def _bbox_cache_key(bounds: Tuple[float, float, float, float]) -> str:
    """Stable short hash for a (rounded) bbox, used to key per-bbox caches."""
    rounded = tuple(round(v, 5) for v in bounds)
    raw = ",".join(str(v) for v in rounded)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


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


def _haversine_m_np(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Vectorized great-circle distance in metres between two point arrays."""
    rlat1, rlon1, rlat2, rlon2 = np.radians(lat1), np.radians(lon1), np.radians(lat2), np.radians(lon2)
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = np.sin(dlat / 2) ** 2 + np.cos(rlat1) * np.cos(rlat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def _interpolate_points(
    coords: List[Tuple[float, float]], interval_m: float = INTERPOLATION_INTERVAL_M
) -> List[Tuple[float, float]]:
    """
    Fill in points along a polyline so no gap exceeds *interval_m* metres.

    Prevents tile-skipping when summary polylines have sparse GPS points.
    Interior interpolated points are computed for all segments at once with
    numpy; only the (cheap) interleaving with the original endpoints stays
    in Python, since it does no math — just list assembly.
    """
    if len(coords) < 2:
        return list(coords)

    n_segs = len(coords) - 1
    arr = np.asarray(coords, dtype=np.float64)
    lat1, lon1 = arr[:-1, 0], arr[:-1, 1]
    lat2, lon2 = arr[1:, 0], arr[1:, 1]

    seg_dist = _haversine_m_np(lat1, lon1, lat2, lon2)
    steps = np.maximum(np.ceil(seg_dist / interval_m).astype(np.int64), 1)
    interior_counts = steps - 1

    result: List[Tuple[float, float]] = [coords[0]]
    total_interior = int(interior_counts.sum())

    if total_interior == 0:
        result.extend(coords[1:])
        return result

    seg_idx = np.repeat(np.arange(n_segs), interior_counts)
    seg_starts = np.repeat(np.cumsum(interior_counts) - interior_counts, interior_counts)
    local_pos = (np.arange(total_interior) - seg_starts) + 1  # 1-indexed within segment
    fracs = local_pos / steps[seg_idx]

    interp_lat = (lat1[seg_idx] + fracs * (lat2[seg_idx] - lat1[seg_idx])).tolist()
    interp_lon = (lon1[seg_idx] + fracs * (lon2[seg_idx] - lon1[seg_idx])).tolist()
    interior_counts_list = interior_counts.tolist()

    pos = 0
    for i in range(n_segs):
        c = interior_counts_list[i]
        if c:
            result.extend(zip(interp_lat[pos:pos + c], interp_lon[pos:pos + c]))
            pos += c
        result.append(coords[i + 1])

    return result


def _segment_tiles(lat1: float, lon1: float, lat2: float, lon2: float, zoom: int) -> List[Tuple[int, int]]:
    """
    Exact set of tiles a GPS segment passes through, via grid traversal
    (2D DDA / "supercover line", per Amanatides & Woo) in continuous
    tile-space rather than sampling points at a fixed interval.

    This replaces distance-based interpolation for tile coverage: instead
    of guessing how finely to resample a segment so no tile gets skipped
    (and re-tuning that guess per zoom level), it walks the exact set of
    grid cells the line crosses — O(tiles crossed) instead of O(samples),
    and correct at any zoom without a tunable interval. This is what makes
    squadratinho (zoom 17) coverage tractable: a sparse, simplified summary
    polyline with long segments no longer needs thousands of interpolated
    samples per segment, just the handful of tiles it actually crosses.
    """
    n = 2 ** zoom
    fx1 = (lon1 + 180.0) / 360.0 * n
    fx2 = (lon2 + 180.0) / 360.0 * n
    fy1 = (1.0 - math.asinh(math.tan(math.radians(lat1))) / math.pi) / 2.0 * n
    fy2 = (1.0 - math.asinh(math.tan(math.radians(lat2))) / math.pi) / 2.0 * n

    x0, y0 = int(fx1), int(fy1)
    x1, y1 = int(fx2), int(fy2)

    if x0 == x1 and y0 == y1:
        return [(x0, y0)]

    dx, dy = fx2 - fx1, fy2 - fy1
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1

    if dx != 0:
        t_delta_x = abs(1.0 / dx)
        t_max_x = ((x0 + (1 if step_x > 0 else 0)) - fx1) / dx
    else:
        t_delta_x = t_max_x = float("inf")

    if dy != 0:
        t_delta_y = abs(1.0 / dy)
        t_max_y = ((y0 + (1 if step_y > 0 else 0)) - fy1) / dy
    else:
        t_delta_y = t_max_y = float("inf")

    x, y = x0, y0
    tiles = [(x, y)]
    # Safety cap: a single segment shouldn't legitimately cross more tiles
    # than this even at squadratinho zoom; guards against pathological
    # data (e.g. a corrupted point pair spanning half the globe).
    for _ in range(20_000):
        if (x, y) == (x1, y1):
            break
        if t_max_x < t_max_y:
            x += step_x
            t_max_x += t_delta_x
        else:
            y += step_y
            t_max_y += t_delta_y
        tiles.append((x, y))

    return tiles


def _activity_tiles(coords: List[Tuple[float, float]], zoom: int) -> Set[Tuple[int, int]]:
    """All tiles an activity's decoded GPS track passes through, exactly."""
    if not coords:
        return set()
    if len(coords) == 1:
        lat, lon = coords[0]
        return {lat_lon_to_tile(lat, lon, zoom)}

    tiles: Set[Tuple[int, int]] = set()
    for i in range(1, len(coords)):
        lat1, lon1 = coords[i - 1]
        lat2, lon2 = coords[i]
        tiles.update(_segment_tiles(lat1, lon1, lat2, lon2, zoom))
    return tiles


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

    def tiles_crossed_by_path(
        self, coords: List[Tuple[float, float]], zoom: int
    ) -> Set[Tuple[int, int]]:
        """All tiles an arbitrary lat/lon path crosses, exactly.

        Same exact grid-traversal ground truth used for scoring recorded
        activities (`_activity_tiles`), exposed so a *planned* route (e.g. an
        ORS road-route polyline that hasn't been ridden yet) can be checked
        against it before claiming tile coverage in the UI.
        """
        return _activity_tiles(coords, zoom)

    # ------------------------------------------------------------------
    # Tile coverage
    # ------------------------------------------------------------------

    def get_tile_coverage(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: Optional[int] = None,
    ) -> TileCoverage:
        """
        Compute tile coverage within a bounding box.

        Args:
            bounds: (south, west, north, east) in degrees
            zoom: tile zoom level — TILE_ZOOM (squadrat) or SQUADRATINHO_ZOOM
                (squadratinho). Defaults to the configured zoom.

        Returns:
            TileCoverage with visited tile data and stats
        """
        zoom = zoom or self.zoom
        cache_path = self.cache_dir / f"coverage_tiles_{zoom}_{_bounds_key(bounds)}.json"
        cached = self._load_tile_cache(cache_path)
        if cached is not None:
            return cached

        south, west, north, east = bounds
        activities = self._load_activities()

        min_tx, min_ty = lat_lon_to_tile(north, west, zoom)
        max_tx, max_ty = lat_lon_to_tile(south, east, zoom)

        visited: Dict[str, dict] = {}

        for act in activities:
            coords = self._decode_activity_coords(act)
            if not coords:
                continue

            start = act.get("start_latlng")
            if start and len(start) == 2:
                slat, slon = start
                if slat < south - 0.1 or slat > north + 0.1 or slon < west - 0.1 or slon > east + 0.1:
                    end = act.get("end_latlng")
                    if end and len(end) == 2:
                        elat, elon = end
                        if elat < south - 0.1 or elat > north + 0.1 or elon < west - 0.1 or elon > east + 0.1:
                            continue

            act_id = act.get("id")
            act_date = act.get("start_date", "")

            for tx, ty in _activity_tiles(coords, zoom):
                if not (min_tx <= tx <= max_tx and min_ty <= ty <= max_ty):
                    continue
                key = f"{tx},{ty}"
                if key not in visited:
                    visited[key] = {
                        "first_ridden": act_date,
                        "activity_ids": [act_id],
                    }
                elif act_id not in visited[key]["activity_ids"]:
                    visited[key]["activity_ids"].append(act_id)

        total_tiles = (max_tx - min_tx + 1) * (max_ty - min_ty + 1)

        result = TileCoverage(
            visited=visited,
            total_in_bounds=max(total_tiles, 1),
            bounds=bounds,
            computed_at=datetime.utcnow().isoformat(),
            zoom=zoom,
        )

        self._save_tile_cache(cache_path, result)
        return result

    def get_tile_coverage_all(self, zoom: Optional[int] = None) -> TileCoverage:
        """
        Compute tile coverage across ALL activities (no bounds filter).

        Useful for getting overall stats and the full visited tile set.
        """
        zoom = zoom or self.zoom
        cache_path = self.cache_dir / f"coverage_tiles_{zoom}_all.json"
        cached = self._load_tile_cache(cache_path)
        if cached is not None:
            return cached

        activities = self._load_activities()
        visited: Dict[str, dict] = {}

        for act in activities:
            coords = self._decode_activity_coords(act)
            if not coords:
                continue

            act_id = act.get("id")
            act_date = act.get("start_date", "")

            for tx, ty in _activity_tiles(coords, zoom):
                key = f"{tx},{ty}"
                if key not in visited:
                    visited[key] = {
                        "first_ridden": act_date,
                        "activity_ids": [act_id],
                    }
                elif act_id not in visited[key]["activity_ids"]:
                    visited[key]["activity_ids"].append(act_id)

        bounds = None
        total_in_bounds = len(visited)
        if visited:
            xs = [int(k.split(",")[0]) for k in visited]
            ys = [int(k.split(",")[1]) for k in visited]
            min_tx, max_tx = min(xs), max(xs)
            min_ty, max_ty = min(ys), max(ys)
            south, west, _, _ = tile_to_bounds(min_tx, max_ty, zoom)
            _, _, north, east = tile_to_bounds(max_tx, min_ty, zoom)
            bounds = (south, west, north, east)
            total_in_bounds = max((max_tx - min_tx + 1) * (max_ty - min_ty + 1), 1)

        result = TileCoverage(
            visited=visited,
            total_in_bounds=total_in_bounds,
            bounds=bounds,
            computed_at=datetime.utcnow().isoformat(),
            zoom=zoom,
        )

        self._save_tile_cache(cache_path, result)
        return result

    # ------------------------------------------------------------------
    # Road coverage (Phase 1B — osmnx-based map matching)
    # ------------------------------------------------------------------

    def _get_or_fetch_road_graph(self, bounds: Tuple[float, float, float, float]):
        """Load the cached bike-network graph for `bounds`, fetching from OSM
        via osmnx if no cache exists yet. Used by road coverage (#481).

        Returns the graph, or raises whatever osmnx raises on fetch failure.
        """
        import osmnx as ox

        south, west, north, east = bounds
        graph_cache = self.cache_dir / f"road_network_{_bbox_cache_key(bounds)}.graphml"

        if graph_cache.exists():
            try:
                G = ox.load_graphml(graph_cache)
                logger.info("Loaded cached road network from %s", graph_cache)
                return G
            except Exception:
                pass

        logger.info("Fetching road network from OSM for bounds %s", bounds)
        G = ox.graph_from_bbox(
            bbox=(north, south, east, west),
            network_type="bike",
            simplify=True,
        )
        ox.save_graphml(G, graph_cache)
        secure_chmod(graph_cache)
        self._evict_old_road_network_caches()
        return G

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

        try:
            G = self._get_or_fetch_road_graph(bounds)
        except Exception as exc:
            logger.error("Failed to fetch road network: %s", exc)
            return {"status": "error", "message": str(exc)}

        edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
        snap_tolerance = self.config.get("exploration.snap_tolerance_meters", 30)
        snap_deg = snap_tolerance / 111_000

        valid_geoms = edges["geometry"].dropna()
        edge_geoms = list(valid_geoms)
        edge_keys = list(valid_geoms.index)

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

    def _get_or_fetch_water_polygons(
        self, bounds: Tuple[float, float, float, float]
    ) -> List[List[Tuple[float, float]]]:
        """Load cached open-water polygons for `bounds`, querying Overpass
        (OSM `natural=water` ways/relations) if no cache exists yet.

        Returns a list of polygons, each a list of (lat, lon) ring points.
        Pure-Python/`requests` only — no osmnx/shapely — so this works
        without a full bike-network graph fetch.
        """
        cache_file = self.cache_dir / f"water_{_bbox_cache_key(bounds)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        south, west, north, east = bounds
        query = (
            "[out:json][timeout:25];"
            "("
            f'way["natural"="water"]({south},{west},{north},{east});'
            f'relation["natural"="water"]({south},{west},{north},{east});'
            ");"
            "out geom;"
        )
        # Overpass rejects requests with no/default User-Agent (406).
        headers = {"User-Agent": "ride-optimizer (exploration water-tile lookup)"}
        response = requests.post(_OVERPASS_URL, data={"data": query}, headers=headers, timeout=30)
        response.raise_for_status()
        elements = response.json().get("elements", [])

        polygons: List[List[Tuple[float, float]]] = []
        for element in elements:
            if element.get("type") == "way" and element.get("geometry"):
                ring = [(pt["lat"], pt["lon"]) for pt in element["geometry"]]
                if len(ring) >= 3:
                    polygons.append(ring)
            elif element.get("type") == "relation":
                for member in element.get("members", []):
                    if member.get("role") == "outer" and member.get("geometry"):
                        ring = [(pt["lat"], pt["lon"]) for pt in member["geometry"]]
                        if len(ring) >= 3:
                            polygons.append(ring)

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(polygons, f)
            secure_chmod(cache_file)
            self._evict_old_water_polygon_caches()
        except OSError as exc:
            logger.warning("Failed to write water polygon cache: %s", exc)

        return polygons

    @staticmethod
    def _point_in_polygon(lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
        """Ray-casting point-in-polygon test (no shapely required)."""
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            yi, xi = polygon[i]
            yj, xj = polygon[j]
            if (yi > lat) != (yj > lat):
                x_at_lat = (xj - xi) * (lat - yi) / (yj - yi) + xi
                if lon < x_at_lat:
                    inside = not inside
            j = i
        return inside

    def get_roadless_tiles(
        self,
        bounds: Tuple[float, float, float, float],
        zoom: Optional[int] = None,
    ) -> dict:
        """Find tiles within `bounds` that fall inside open water (lakes,
        reservoirs, and similar bodies tagged `natural=water` in OSM).

        The exploration route generator uses this to exclude tiles that
        aren't bikeable or walkable from "new tile" scoring, so routes stop
        being pulled toward tiles they have no way to enter (#525). Queries
        Overpass directly with a pure-Python point-in-polygon test — no
        osmnx/shapely dependency — so it doesn't need a full bike-network
        graph fetch. This only catches open water, not genuinely roadless
        (but dry) terrain that the old osmnx-graph-absence check also caught.
        """
        zoom = zoom or self.zoom

        try:
            polygons = self._get_or_fetch_water_polygons(bounds)
        except Exception as exc:
            logger.error("Failed to fetch water polygons: %s", exc)
            return {"status": "error", "message": str(exc)}

        south, west, north, east = bounds
        min_tx, min_ty = lat_lon_to_tile(north, west, zoom)
        max_tx, max_ty = lat_lon_to_tile(south, east, zoom)

        roadless: List[Dict[str, int]] = []
        for tx in range(min_tx, max_tx + 1):
            for ty in range(min_ty, max_ty + 1):
                t_south, t_west, t_north, t_east = tile_to_bounds(tx, ty, zoom)
                center_lat = (t_south + t_north) / 2
                center_lon = (t_west + t_east) / 2
                if any(self._point_in_polygon(center_lat, center_lon, poly) for poly in polygons):
                    roadless.append({"x": tx, "y": ty})

        return {
            "status": "success",
            "zoom": zoom,
            "roadless": roadless,
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
                zoom=data.get("zoom", TILE_ZOOM),
            )
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _save_tile_cache(self, path: Path, coverage: TileCoverage) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(coverage.to_dict(), f)
            secure_chmod(path)
        except OSError as exc:
            logger.warning("Failed to write tile cache: %s", exc)

    def _evict_old_road_network_caches(self) -> None:
        """Keep at most MAX_ROAD_NETWORK_CACHES road_network_*.graphml files,
        evicting the least-recently-modified ones beyond that cap."""
        caches = sorted(
            self.cache_dir.glob("road_network_*.graphml"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for p in caches[MAX_ROAD_NETWORK_CACHES:]:
            try:
                p.unlink()
            except OSError:
                pass

    def _evict_old_water_polygon_caches(self) -> None:
        """Keep at most MAX_WATER_POLYGON_CACHES water_*.json files,
        evicting the least-recently-modified ones beyond that cap."""
        caches = sorted(
            self.cache_dir.glob("water_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for p in caches[MAX_WATER_POLYGON_CACHES:]:
            try:
                p.unlink()
            except OSError:
                pass

    def invalidate_caches(self) -> None:
        """Remove all coverage caches (call after new activities are fetched)."""
        self._activities_cache = None
        for p in self.cache_dir.glob("coverage_tiles_*.json"):
            try:
                p.unlink()
            except OSError:
                pass
        for p in self.cache_dir.glob("road_network_*.graphml"):
            try:
                p.unlink()
            except OSError:
                pass
        # Water polygons don't change with new activities — not evicted here.
        # Legacy unkeyed cache filename from before bbox-keyed caching (#481).
        legacy_cache = self.cache_dir / "road_network.graphml"
        if legacy_cache.exists():
            try:
                legacy_cache.unlink()
            except OSError:
                pass
        logger.info("Coverage caches invalidated")
