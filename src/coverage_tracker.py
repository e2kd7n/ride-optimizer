"""
Coverage tracking for exploration route generation.

Computes which map tiles have been ridden based on cached Strava activity
GPS tracks. (An earlier osmnx-based road-segment coverage feature was
removed in #581 — it required osmnx/shapely, which were never added to
requirements.txt, so it could only ever 500 in production; superseded by
the tile-coverage/squadrat approach below.)
"""

import json
import hashlib
import os
from src.secure_logger import SecureLogger
import math
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import polyline as polyline_codec
import requests

from src.json_storage import secure_chmod

logger = SecureLogger(__name__)

TILE_ZOOM = 14              # "squadrat" granularity (squadrat.at / squadrat.com default)
SQUADRATINHO_ZOOM = 17      # "squadratinho" granularity — each squadrat = 8x8 squadratinhos
MAX_WATER_POLYGON_CACHES = 20  # cap on retained water_<hash>.json files
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Overpass's own internal query budget ([out:json][timeout:N]) and the
# client-side requests.post timeout (#562) — lowered together from the
# previous 25/30s. The client timeout stays a couple seconds above the
# query timeout so we don't abort a query Overpass would've legitimately
# finished (lowering only the client side would do exactly that).
_OVERPASS_QUERY_TIMEOUT_S = 10
_OVERPASS_REQUEST_TIMEOUT_S = 12
# Short-lived "this endpoint just failed" marker (#562), keyed by endpoint
# rather than by bbox: an outage is global to the endpoint, but the query
# bbox changes on nearly every pin placement, so a bbox-keyed marker would
# almost always miss and every request would still pay the full timeout.
_OVERPASS_NEGATIVE_CACHE_TTL_S = 60


#: Placeholder value for a visited tile in a TileCoverage response (#579).
#: Every consumer (exploration-worker.js, explore.js's drawTileGrid) only
#: ever reads Object.keys(coverageData.visited) — the per-tile
#: {"first_ridden": ..., "activity_ids": [...]} detail the tile index keeps
#: internally was being shipped over the wire and silently discarded on
#: every request. At full-history scale (65k+ tiles observed in
#: production) that's several MB of wasted payload over cellular. The full
#: detail still lives in the on-disk/in-memory tile index (see
#: _build_or_update_tile_index) for incremental-update bookkeeping — only
#: the response-building path (get_tile_coverage/get_tile_coverage_all)
#: drops it before handing tiles to a caller.
_TRIMMED_TILE_VALUE = 1


@dataclass
class TileCoverage:
    """Result of tile coverage computation.

    `visited` maps tile key ("x,y") to a trimmed placeholder value (#579),
    not the tile index's full per-tile detail — see _TRIMMED_TILE_VALUE.
    """
    visited: Dict[str, int] = field(default_factory=dict)
    total_in_bounds: int = 0
    bounds: Optional[Tuple[float, float, float, float]] = None
    computed_at: str = ""
    zoom: int = TILE_ZOOM
    # True when this snapshot was served from the last-published tile index
    # instead of waiting on an in-progress rebuild for this zoom (#563) — a
    # cold rebuild (or a #560 startup pre-warm) can take multiple seconds,
    # and a caller on a short client-side timeout would rather get an
    # immediate, possibly-slightly-stale answer than block for the full
    # rebuild. False for every normal (fresh-or-freshly-built) response.
    stale: bool = False

    @property
    def visited_count(self) -> int:
        return len(self.visited)

    @property
    def coverage_pct(self) -> float:
        if self.total_in_bounds == 0:
            return 0.0
        # get_tile_coverage_all() (#556) trims outlier tiles out of `bounds`/
        # `total_in_bounds` while keeping the full ridden-tile set in `visited`
        # (so a genuinely-ridden far-away tile still shows up on the map) — so
        # visited_count can, in principle, include a handful of tiles outside
        # the reported bounds. Cap at 100% rather than surface a nonsensical
        # >100% "coverage" figure; the trimmed denominator is deliberately a
        # "core riding area" estimate, not a strict superset guarantee.
        return round(min(100.0, self.visited_count / self.total_in_bounds * 100), 1)

    def to_dict(self) -> dict:
        return {
            "visited": self.visited,
            "total_in_bounds": self.total_in_bounds,
            "visited_count": self.visited_count,
            "coverage_pct": self.coverage_pct,
            "bounds": self.bounds,
            "computed_at": self.computed_at,
            "zoom": self.zoom,
            "stale": self.stale,
        }


def _bbox_cache_key(bounds: Tuple[float, float, float, float]) -> str:
    """Stable short hash for a (rounded) bbox, used to key per-bbox caches."""
    rounded = tuple(round(v, 5) for v in bounds)
    raw = ",".join(str(v) for v in rounded)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


# Tukey's-fences trimming for _robust_tile_range (#556): a single activity
# geographically far from a rider's normal riding area (a trip, or a
# corrupted/erroneous GPS point) otherwise balloons get_tile_coverage_all()'s
# reported bounds to span the outlier, driving total_in_bounds into the tens
# of millions and coverage_pct to a permanent ~0% — verified on production
# data (5,849 visited tiles, but a bbox spanning nearly the whole globe).
_OUTLIER_IQR_MULTIPLIER = 3
# Below this many points, percentile statistics are too noisy to trust —
# just use the raw range (matches pre-fix behavior for small datasets).
_OUTLIER_MIN_SAMPLES = 20


def _robust_tile_range(coords: List[int]) -> Tuple[int, int]:
    """(min, max) of `coords`, excluding extreme outliers via Tukey's fences.

    Applied independently per axis (x, then y) since the bounding box this
    feeds is inherently an axis-aligned rectangle — an outlier tile's x and y
    don't need to be jointly extreme to distort that rectangle on one side.
    Falls back to the raw min/max when there are too few points to trust
    percentile statistics, or when the interquartile range is zero (a tight,
    degenerate cluster with no meaningful spread to trim).
    """
    if len(coords) < _OUTLIER_MIN_SAMPLES:
        return min(coords), max(coords)

    arr = np.asarray(coords)
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    if iqr == 0:
        return int(arr.min()), int(arr.max())

    lower = q1 - _OUTLIER_IQR_MULTIPLIER * iqr
    upper = q3 + _OUTLIER_IQR_MULTIPLIER * iqr
    filtered = arr[(arr >= lower) & (arr <= upper)]
    if filtered.size == 0:
        return int(arr.min()), int(arr.max())
    return int(filtered.min()), int(filtered.max())


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


class CoverageTracker:
    """Compute tile coverage from Strava activity GPS data."""

    def __init__(self, config):
        self.config = config
        self.zoom = config.get("exploration.tile_zoom_level", TILE_ZOOM)
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        removed = self._sweep_legacy_coverage_tile_files()
        if removed:
            logger.info("Removed %d legacy coverage_tiles_*.json cache file(s) (#555)", removed)
        self._activities_cache: Optional[List[dict]] = None
        # In-memory copy of each zoom's tile index (see _build_or_update_tile_index),
        # keyed by zoom. Avoids re-reading/re-parsing the on-disk index on every
        # request once a worker thread has built it once.
        self._tile_index_cache: Dict[int, dict] = {}
        # Per-zoom locks (#558) rather than one lock shared across every
        # zoom — a cold rebuild at one zoom (e.g. squadratinho, zoom 17)
        # would otherwise serialize reads/writes at an already-warm zoom
        # (squadrat, zoom 14) behind it. Lazily created per zoom by
        # _get_zoom_lock(); _tile_index_locks_lock guards only that
        # lazy-creation step, never held across a build/read.
        self._tile_index_locks: Dict[int, threading.Lock] = {}
        self._tile_index_locks_lock = threading.Lock()
        # Negative cache for Overpass failures (#562): endpoint -> wall-clock
        # timestamp until which fresh requests fail fast instead of retrying.
        self._overpass_failure_until: Dict[str, float] = {}
        self._overpass_failure_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Activity loading
    # ------------------------------------------------------------------

    def _load_activities(self) -> List[dict]:
        """Load cached Strava activities (lazy, cached in memory per process)."""
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

    def _tile_index_path(self, zoom: int) -> Path:
        return self.cache_dir / f"tile_index_{zoom}.json"

    def _load_tile_index_from_disk(self, zoom: int) -> Optional[dict]:
        path = self._tile_index_path(zoom)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "indexed_activity_ids": set(data["indexed_activity_ids"]),
                "tiles": data["tiles"],
            }
        except (json.JSONDecodeError, OSError, KeyError):
            logger.warning("Tile index cache at %s is missing/corrupt — will rebuild", path)
            return None

    def _write_tile_index_atomic(self, zoom: int, index: dict) -> None:
        """Atomic write (temp file + os.replace) so a mid-write crash or a
        concurrent reader never observes a torn/partial JSON file."""
        path = self._tile_index_path(zoom)
        payload = {
            "indexed_activity_ids": sorted(index["indexed_activity_ids"]),
            "tiles": index["tiles"],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp_path = path.with_name(f"{path.name}.tmp{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            secure_chmod(tmp_path)
            os.replace(tmp_path, path)
            secure_chmod(path)
        except OSError as exc:
            logger.warning("Failed to write tile index cache: %s", exc)
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _get_zoom_lock(self, zoom: int) -> threading.Lock:
        """Return the lock guarding zoom `zoom`'s tile index, creating it on
        first use (#558). Per-zoom rather than one global lock so a cold
        rebuild at one zoom doesn't block reads/writes at an already-warm
        zoom. The outer unlocked check avoids taking
        _tile_index_locks_lock on every call once a zoom's lock exists.
        """
        lock = self._tile_index_locks.get(zoom)
        if lock is not None:
            return lock
        with self._tile_index_locks_lock:
            lock = self._tile_index_locks.get(zoom)
            if lock is None:
                lock = threading.Lock()
                self._tile_index_locks[zoom] = lock
            return lock

    def _build_or_update_tile_index(self, zoom: int) -> dict:
        """Return {"indexed_activity_ids": set, "tiles": dict} for `zoom`,
        the full set of tiles ever ridden at that zoom level, keyed "x,y".

        Replaces the old per-bbox rescan-from-scratch cache: every activity's
        polyline is decoded and folded into this index at most once (tracked
        by activity id, not a "last id" watermark — data_fetcher.py rewrites
        activities.json as a merged-and-resorted whole on every fetch, so a
        watermark would miss activities inserted anywhere but the tail).
        Bbox queries (get_tile_coverage) then just filter this flat dict by
        tile range — no polyline decoding on the request path at all once the
        index is warm.

        invalidate_caches() now runs automatically after every activity
        fetch/analyze/backfill (see the three call sites in
        app/api/data_bp.py) and clears the in-memory index/activities cache
        so this call reloads from disk and diffs against fresh data (#571).
        This also self-heals independent of that, on *every* call, by
        diffing the currently-loaded activity ids against what's indexed
        rather than assuming the index is fresh just because it exists on
        disk — that still matters for e.g. a long-running dev process, or
        any other path that touches activities.json without going through
        invalidate_caches().

        Guarded by a per-zoom lock (#558), not one lock shared across every
        zoom, so a cold rebuild at one zoom doesn't serialize reads/writes
        at an already-warm zoom behind it. Updates are copy-on-write: when
        new activities need folding in, this builds a *new* tiles dict (and
        a new entry dict for any tile a new activity touches) instead of
        mutating the previously-published one in place, then publishes the
        result with a single `self._tile_index_cache[zoom] = index`
        assignment — atomic under the GIL. A caller that grabbed a
        reference to the old `index` before this ran (e.g. get_tile_coverage(),
        which iterates index["tiles"] *after* this lock is released) keeps
        iterating a snapshot that's never mutated out from under it, no
        matter what runs next. This is what fixes the dict-mutated-during-
        iteration race from #559 (merged into #558): under the old design,
        a concurrent rebuild mutated the exact same dict object a reader
        elsewhere was iterating.
        """
        with self._get_zoom_lock(zoom):
            return self._build_or_update_tile_index_locked(zoom)

    def _build_or_update_tile_index_locked(self, zoom: int) -> dict:
        """Body of _build_or_update_tile_index(), assuming the caller
        already holds self._get_zoom_lock(zoom). Split out so
        _get_tile_index_or_stale() (#563) can do its own non-blocking
        `acquire` and then run the exact same build logic, instead of
        duplicating it."""
        index = self._tile_index_cache.get(zoom)
        if index is None:
            index = self._load_tile_index_from_disk(zoom)
        if index is None:
            index = {"indexed_activity_ids": set(), "tiles": {}}

        activities = self._load_activities()
        current_ids = {a.get("id") for a in activities if a.get("id") is not None}
        new_ids = current_ids - index["indexed_activity_ids"]

        if new_ids:
            start = time.monotonic()
            decoded_count = 0
            # Shallow copies: existing tile entries are shared objects
            # with the previously-published index until this loop
            # touches them, at which point a *new* entry dict/list is
            # substituted in new_tiles rather than the shared one being
            # mutated in place (see docstring above).
            new_tiles = dict(index["tiles"])
            new_indexed_ids = set(index["indexed_activity_ids"])
            for act in activities:
                act_id = act.get("id")
                if act_id not in new_ids:
                    continue
                coords = self._decode_activity_coords(act)
                decoded_count += 1
                if coords:
                    act_date = act.get("start_date", "")
                    for tx, ty in _activity_tiles(coords, zoom):
                        key = f"{tx},{ty}"
                        entry = new_tiles.get(key)
                        if entry is None:
                            new_tiles[key] = {"first_ridden": act_date, "activity_ids": [act_id]}
                        elif act_id not in entry["activity_ids"]:
                            new_tiles[key] = {
                                "first_ridden": entry["first_ridden"],
                                "activity_ids": entry["activity_ids"] + [act_id],
                            }
                new_indexed_ids.add(act_id)

            index = {"indexed_activity_ids": new_indexed_ids, "tiles": new_tiles}

            logger.info(
                "Tile index (zoom=%d) updated: %d new activities decoded in %.2fs (total indexed=%d, tiles=%d)",
                zoom, decoded_count, time.monotonic() - start,
                len(index["indexed_activity_ids"]), len(index["tiles"]),
            )
            self._write_tile_index_atomic(zoom, index)

        self._tile_index_cache[zoom] = index
        return index

    def _get_tile_index_or_stale(self, zoom: int) -> Tuple[dict, bool]:
        """Non-blocking tile-index fetch for the request path (#563).

        Returns (index, stale). If zoom's lock is free, this acquires it
        and runs the normal build/update in-line (stale=False) — identical
        to calling _build_or_update_tile_index(zoom) directly. If the lock
        is already held (a rebuild — cold start, #560 pre-warm, or another
        request — is in progress for this zoom), this does NOT block:
        it immediately returns the last-published in-memory snapshot
        (stale=True) so the caller can respond right away instead of
        waiting out the full rebuild. The rebuild already in progress
        continues in the background under the lock as before and will
        publish a fresh snapshot for the next request.

        Falls back to the normal blocking build only when there is no
        snapshot at all yet to serve as "stale" — a genuinely cold zoom
        with two first-requests racing each other, where returning nothing
        would be worse than a brief wait.
        """
        lock = self._get_zoom_lock(zoom)
        if lock.acquire(blocking=False):
            try:
                return self._build_or_update_tile_index_locked(zoom), False
            finally:
                lock.release()

        cached = self._tile_index_cache.get(zoom)
        if cached is not None:
            logger.info(
                "get_tile_coverage(zoom=%d): rebuild already in progress — serving stale snapshot (%d tiles)",
                zoom, len(cached["tiles"]),
            )
            return cached, True

        logger.info(
            "get_tile_coverage(zoom=%d): rebuild in progress and no snapshot published yet — blocking",
            zoom,
        )
        return self._build_or_update_tile_index(zoom), False

    def get_tile_coverage(
        self,
        bounds: Optional[Tuple[float, float, float, float]],
        zoom: Optional[int] = None,
    ) -> TileCoverage:
        """
        Compute tile coverage within a bounding box.

        Filters the persisted, incrementally-updated per-zoom tile index
        (`_build_or_update_tile_index`) down to `bounds`, instead of
        rescanning every activity per viewport. The viewport bbox changes on
        nearly every request (pan/zoom/new start point), so caching per-bbox
        on disk was an almost-always-miss cache that forced a full
        recompute — decoding every activity's polyline and walking its
        tiles — on effectively every Explore page load.

        Args:
            bounds: (south, west, north, east) in degrees, or None for the
                full-history view (delegates to get_tile_coverage_all).
            zoom: tile zoom level — TILE_ZOOM (squadrat) or SQUADRATINHO_ZOOM
                (squadratinho). Defaults to the configured zoom.

        Returns:
            TileCoverage with visited tile data and stats
        """
        zoom = zoom or self.zoom
        if bounds is None:
            return self.get_tile_coverage_all(zoom=zoom)

        start = time.monotonic()
        index, stale = self._get_tile_index_or_stale(zoom)

        south, west, north, east = bounds
        min_tx, min_ty = lat_lon_to_tile(north, west, zoom)
        max_tx, max_ty = lat_lon_to_tile(south, east, zoom)

        visited: Dict[str, int] = {}
        for key in index["tiles"]:
            tx_str, ty_str = key.split(",")
            tx, ty = int(tx_str), int(ty_str)
            if min_tx <= tx <= max_tx and min_ty <= ty <= max_ty:
                visited[key] = _TRIMMED_TILE_VALUE

        total_tiles = (max_tx - min_tx + 1) * (max_ty - min_ty + 1)

        logger.info(
            "get_tile_coverage(zoom=%d) served from index in %.3fs "
            "(%d visited-in-bbox / %d total tiles indexed, stale=%s)",
            zoom, time.monotonic() - start, len(visited), len(index["tiles"]), stale,
        )

        return TileCoverage(
            visited=visited,
            total_in_bounds=max(total_tiles, 1),
            bounds=bounds,
            computed_at=datetime.now(timezone.utc).isoformat(),
            zoom=zoom,
            stale=stale,
        )

    def get_tile_coverage_all(self, zoom: Optional[int] = None) -> TileCoverage:
        """
        Compute tile coverage across ALL activities (no bounds filter).

        Useful for getting overall stats and the full visited tile set.
        """
        zoom = zoom or self.zoom
        index = self._build_or_update_tile_index(zoom)
        visited = {key: _TRIMMED_TILE_VALUE for key in index["tiles"]}

        bounds = None
        total_in_bounds = len(visited)
        if visited:
            xs = [int(k.split(",")[0]) for k in visited]
            ys = [int(k.split(",")[1]) for k in visited]
            # Robust to outlier tiles (#556) — see _robust_tile_range.
            min_tx, max_tx = _robust_tile_range(xs)
            min_ty, max_ty = _robust_tile_range(ys)
            south, west, _, _ = tile_to_bounds(min_tx, max_ty, zoom)
            _, _, north, east = tile_to_bounds(max_tx, min_ty, zoom)
            bounds = (south, west, north, east)
            total_in_bounds = max((max_tx - min_tx + 1) * (max_ty - min_ty + 1), 1)

        return TileCoverage(
            visited=visited,
            total_in_bounds=total_in_bounds,
            bounds=bounds,
            computed_at=datetime.now(timezone.utc).isoformat(),
            zoom=zoom,
        )

    # ------------------------------------------------------------------
    # Water polygons (open-water tile exclusion, #525)
    # ------------------------------------------------------------------

    def _get_or_fetch_water_polygons(
        self, bounds: Tuple[float, float, float, float]
    ) -> List[List[List[float]]]:
        """Load cached open-water polygons for `bounds`, querying Overpass
        (OSM `natural=water` ways/relations) if no cache exists yet.

        Returns a list of polygons, each a list of [lat, lon] ring points.
        A freshly-fetched result builds these as (lat, lon) tuples, but the
        far more common cache-hit path returns whatever json.load() gave
        back — plain lists, since JSON has no tuple type — so the
        annotation reflects that actual (list-of-lists) shape rather than
        the tuple type only the cold-fetch path produces. Pure-Python/
        `requests` only — no osmnx/shapely — so this works without a full
        bike-network graph fetch.
        """
        cache_file = self.cache_dir / f"water_{_bbox_cache_key(bounds)}.json"
        ttl = int(self.config.get("exploration.water_polygon_cache_ttl_seconds", 0))
        if cache_file.exists():
            age_s = time.time() - cache_file.stat().st_mtime
            if ttl <= 0 or age_s <= ttl:
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass
            else:
                logger.info(
                    "Water polygon cache %s is %.0fs old (TTL %ds) — refetching",
                    cache_file, age_s, ttl,
                )

        # Negative cache (#562): skip straight to failure if Overpass failed
        # recently rather than paying out another ~12s timeout for a query
        # that's very likely to fail again during an outage.
        with self._overpass_failure_lock:
            failure_until = self._overpass_failure_until.get(_OVERPASS_URL)
        if failure_until is not None and time.time() < failure_until:
            remaining = failure_until - time.time()
            logger.warning(
                "Overpass endpoint recently failed — skipping retry for %.0fs more", remaining,
            )
            raise RuntimeError(
                f"Overpass water-polygon lookup temporarily unavailable ({remaining:.0f}s)"
            )

        south, west, north, east = bounds
        query = (
            f"[out:json][timeout:{_OVERPASS_QUERY_TIMEOUT_S}];"
            "("
            f'way["natural"="water"]({south},{west},{north},{east});'
            f'relation["natural"="water"]({south},{west},{north},{east});'
            ");"
            "out geom;"
        )
        # Overpass rejects requests with no/default User-Agent (406).
        headers = {"User-Agent": "ride-optimizer (exploration water-tile lookup)"}
        try:
            response = requests.post(
                _OVERPASS_URL, data={"data": query}, headers=headers,
                timeout=_OVERPASS_REQUEST_TIMEOUT_S,
            )
            response.raise_for_status()
            elements = response.json().get("elements", [])
        except (requests.RequestException, ValueError, OSError) as exc:
            with self._overpass_failure_lock:
                self._overpass_failure_until[_OVERPASS_URL] = time.time() + _OVERPASS_NEGATIVE_CACHE_TTL_S
            logger.warning(
                "Overpass water-polygon query failed: %s — negative-caching endpoint for %ds",
                exc, _OVERPASS_NEGATIVE_CACHE_TTL_S,
            )
            raise

        # A successful call clears any earlier failure marker so the next
        # request isn't held back by a now-stale negative cache entry.
        with self._overpass_failure_lock:
            self._overpass_failure_until.pop(_OVERPASS_URL, None)

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

        # Atomic write (temp file + os.replace, #562) — like the tile index
        # and route cache already do — so a concurrent reader can never
        # observe a truncated/partial JSON file mid-write.
        tmp_path = cache_file.with_name(f"{cache_file.name}.tmp{os.getpid()}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(polygons, f)
            secure_chmod(tmp_path)
            os.replace(tmp_path, cache_file)
            secure_chmod(cache_file)
            self._evict_old_water_polygon_caches()
        except OSError as exc:
            logger.warning("Failed to write water polygon cache: %s", exc)
            try:
                tmp_path.unlink()
            except OSError:
                pass

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

    @staticmethod
    def _polygon_bbox(polygon: List[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        """(min_lat, min_lon, max_lat, max_lon) bounding box of a polygon
        ring — a cheap prefilter (#574) computed once per polygon per
        get_roadless_tiles() call, ahead of the full tile sweep."""
        lats = [pt[0] for pt in polygon]
        lons = [pt[1] for pt in polygon]
        return min(lats), min(lons), max(lats), max(lons)

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

        Each polygon's bounding box is precomputed once, before the tile
        sweep (#574), and used as a cheap prefilter: a tile whose center
        falls outside every polygon's bbox is rejected immediately, without
        running the full O(polygon points) ray-cast test at all. This is
        deliberately NOT a per-(bbox,zoom) *result* cache — get_tile_coverage()'s
        own docstring explains why that pattern was dropped elsewhere (an
        almost-always-miss cache, since the viewport bbox changes on nearly
        every request); the bbox prefilter here is a same-call speedup, not
        a cache of this method's output.
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

        polygons_with_bbox = [(poly, self._polygon_bbox(poly)) for poly in polygons]

        roadless: List[Dict[str, int]] = []
        for tx in range(min_tx, max_tx + 1):
            for ty in range(min_ty, max_ty + 1):
                t_south, t_west, t_north, t_east = tile_to_bounds(tx, ty, zoom)
                center_lat = (t_south + t_north) / 2
                center_lon = (t_west + t_east) / 2
                for poly, (p_min_lat, p_min_lon, p_max_lat, p_max_lon) in polygons_with_bbox:
                    # Bbox prefilter: skip the full ray-cast entirely for a
                    # polygon whose bbox can't possibly contain this tile.
                    if not (p_min_lat <= center_lat <= p_max_lat and p_min_lon <= center_lon <= p_max_lon):
                        continue
                    if self._point_in_polygon(center_lat, center_lon, poly):
                        roadless.append({"x": tx, "y": ty})
                        break

        return {
            "status": "success",
            "zoom": zoom,
            "roadless": roadless,
            "bounds": bounds,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

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

    def _sweep_legacy_coverage_tile_files(self) -> int:
        """Delete leftover coverage_tiles_*.json files from the per-bbox
        caching scheme that predates the tile-index rewrite (#555).

        Nothing in the current codebase writes these anymore — coverage is
        served from the persisted, incrementally-updated tile_index_{zoom}.json
        instead. The only previous cleanup was inside invalidate_caches(),
        which only runs on a manual resync; in production that apparently
        never happened — 38 of these files (32MB) were still sitting on the
        Pi over five weeks after the rewrite that made them obsolete. Called
        unconditionally at __init__ so a leftover deployment self-heals on
        its next restart instead of waiting on a resync that may never come.

        Returns the number of files removed.
        """
        removed = 0
        for p in self.cache_dir.glob("coverage_tiles_*.json"):
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        return removed

    def invalidate_caches(self) -> None:
        """Soft-invalidate: clear in-memory state only (#571/#583).

        Drops the cached activities list and the in-memory tile index, so
        the next read reloads the on-disk index and diffs it against
        freshly-loaded activities (see _build_or_update_tile_index) — but
        leaves the on-disk tile_index_{zoom}.json files themselves alone.

        This is what runs automatically after every activity fetch/analyze/
        backfill (the three call sites in app/api/data_bp.py, in turn
        triggered nightly by cron/daily_analysis.py). Those call sites used
        to invoke a fully destructive wipe (see hard_invalidate_caches()
        below) that deleted the on-disk index outright, forcing a full cold
        rebuild — decoding every ridden activity's polyline from scratch —
        on the next Explore page load after every nightly sync. Soft
        invalidation still picks up the new activities (via the diff in
        _build_or_update_tile_index) without paying that cost, since the
        vast majority of previously-indexed tiles didn't change.

        For an explicit, user-initiated "clear my coverage cache" action,
        use hard_invalidate_caches() instead.
        """
        self._activities_cache = None
        self._clear_tile_index_cache()
        logger.info("Coverage caches soft-invalidated (in-memory only)")

    def _clear_tile_index_cache(self) -> None:
        """Drop every zoom's in-memory tile index, one zoom at a time under
        that zoom's own lock (#558) — so this can't race a concurrent
        _build_or_update_tile_index() call for the same zoom (there's no
        single global lock anymore to serialize the two under)."""
        for zoom in set(self._tile_index_cache) | set(self._tile_index_locks):
            with self._get_zoom_lock(zoom):
                self._tile_index_cache.pop(zoom, None)

    def hard_invalidate_caches(self) -> None:
        """Fully wipe all coverage caches, including the on-disk tile index.

        This is the old (pre-#571) invalidate_caches() behaviour, kept
        available for an explicit, user-initiated cache-clear request —
        e.g. after suspected corruption, or a deliberate full rebuild.
        Do NOT wire this into the automatic post-activity-sync path; use
        the soft invalidate_caches() there instead.
        """
        self._activities_cache = None

        # Delete each zoom's on-disk file under that zoom's own lock (#558),
        # so this can't delete a tile_index_{zoom}.json file out from under
        # an in-flight _build_or_update_tile_index() call for the same
        # zoom. Covers zooms known in memory (cache or lock already exists)
        # as well as zooms only seen on disk (e.g. a fresh process that
        # hasn't read/built a given zoom's index yet this run).
        zooms = set(self._tile_index_cache) | set(self._tile_index_locks)
        for path in self.cache_dir.glob("tile_index_*.json"):
            try:
                zooms.add(int(path.stem.rsplit("_", 1)[-1]))
            except ValueError:
                continue
        for zoom in zooms:
            with self._get_zoom_lock(zoom):
                self._tile_index_cache.pop(zoom, None)
                try:
                    self._tile_index_path(zoom).unlink()
                except OSError:
                    pass

        self._sweep_legacy_coverage_tile_files()
        # Water polygons don't change with new activities — not evicted here.
        logger.info("Coverage caches hard-invalidated (on-disk index cleared)")
